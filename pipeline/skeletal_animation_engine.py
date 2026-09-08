#!/usr/bin/env python3
"""
pipeline/skeletal_animation_engine.py: 3D 骨骼蒙皮动画管线 (Skeletal Rigging & Animation Pipeline)
提供纯 Python 标准库实现的骨骼装配、顶点蒙皮权重计算与关键帧动画序列化：
1. JointHierarchy: 标准人体/多足骨骼节点拓扑与逆绑定矩阵 (Inverse Bind Matrices)。
2. SkinWeightCalculator: 柱状与距离衰减的自动顶点权重分配 (JOINTS_0, WEIGHTS_0)。
3. AnimationTrackBuilder: 四元数插值关键帧轨道构建 (Idle 呼吸待机, Walk 对偶走步, Attack 蓄力劈砍)。
4. GLTFSkinExporter: 严格遵循 Khronos glTF 2.0 skins 与 animations 规范的二进制数据流封装。
"""

import os
import sys
import math
import json
import base64
import struct
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# 数学工具类 (四元数与矩阵，纯 Python 实现)
# -----------------------------------------------------------------------------
def quat_from_euler(pitch: float, yaw: float, roll: float) -> Tuple[float, float, float, float]:
    """从欧拉角(弧度)计算四元数 (x, y, z, w)"""
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    mag = math.sqrt(x*x + y*y + z*z + w*w) or 1.0
    return (x/mag, y/mag, z/mag, w/mag)

def quat_slerp(q0: Tuple[float, float, float, float],
               q1: Tuple[float, float, float, float],
               t: float) -> Tuple[float, float, float, float]:
    """四元数球面线性插值"""
    dot = q0[0]*q1[0] + q0[1]*q1[1] + q0[2]*q1[2] + q0[3]*q1[3]
    if dot < 0.0:
        q1 = (-q1[0], -q1[1], -q1[2], -q1[3])
        dot = -dot
    if dot > 0.9995:
        res = tuple((1.0 - t)*a + t*b for a, b in zip(q0, q1))
        mag = math.sqrt(sum(x*x for x in res)) or 1.0
        return tuple(x/mag for x in res)
    theta_0 = math.acos(dot)
    theta = theta_0 * t
    sin_theta = math.sin(theta)
    sin_theta_0 = math.sin(theta_0)
    s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0
    return (s0*q0[0] + s1*q1[0], s0*q0[1] + s1*q1[1], s0*q0[2] + s1*q1[2], s0*q0[3] + s1*q1[3])

def identity_mat4() -> List[float]:
    """4x4 单位矩阵 (Column-major)"""
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    ]

def translation_mat4(tx: float, ty: float, tz: float) -> List[float]:
    """平移矩阵 (Column-major)"""
    m = identity_mat4()
    m[12] = tx
    m[13] = ty
    m[14] = tz
    return m

# -----------------------------------------------------------------------------
# 骨骼数据结构
# -----------------------------------------------------------------------------
@dataclass
class JointNode:
    joint_id: int
    name: str
    parent_id: Optional[int]
    world_pos: Tuple[float, float, float]
    local_translation: Tuple[float, float, float]
    local_rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    children: List[int] = field(default_factory=list)

@dataclass
class KeyframeTrack:
    node_index: int
    property_path: str  # "rotation" 或 "translation"
    timestamps: List[float]
    values: List[float] # 四元数 [x, y, z, w, ...] 或 位移 [x, y, z, ...]

@dataclass
class AnimationClip:
    name: str
    duration: float
    tracks: List[KeyframeTrack] = field(default_factory=list)

# -----------------------------------------------------------------------------
# 标准骨骼层级构建器 (Humanoid & Spider)
# -----------------------------------------------------------------------------
class JointHierarchy:
    @staticmethod
    def create_humanoid_skeleton() -> List[JointNode]:
        """构建 15 关节标准人形骨骼树"""
        joints = [
            # 0: Root / Hips
            JointNode(0, "Hips", None, (0.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
            # 1: Spine
            JointNode(1, "Spine", 0, (0.0, 1.3, 0.0), (0.0, 0.3, 0.0)),
            # 2: Chest
            JointNode(2, "Chest", 1, (0.0, 1.6, 0.0), (0.0, 0.3, 0.0)),
            # 3: Neck
            JointNode(3, "Neck", 2, (0.0, 1.8, 0.0), (0.0, 0.2, 0.0)),
            # 4: Head
            JointNode(4, "Head", 3, (0.0, 2.0, 0.0), (0.0, 0.2, 0.0)),
            # 5: LeftUpperArm
            JointNode(5, "LeftUpperArm", 2, (-0.4, 1.6, 0.0), (-0.4, 0.0, 0.0)),
            # 6: LeftForearm
            JointNode(6, "LeftForearm", 5, (-0.8, 1.6, 0.0), (-0.4, 0.0, 0.0)),
            # 7: RightUpperArm
            JointNode(7, "RightUpperArm", 2, (0.4, 1.6, 0.0), (0.4, 0.0, 0.0)),
            # 8: RightForearm
            JointNode(8, "RightForearm", 7, (0.8, 1.6, 0.0), (0.4, 0.0, 0.0)),
            # 9: LeftThigh
            JointNode(9, "LeftThigh", 0, (-0.2, 1.0, 0.0), (-0.2, 0.0, 0.0)),
            # 10: LeftCalf
            JointNode(10, "LeftCalf", 9, (-0.2, 0.5, 0.0), (0.0, -0.5, 0.0)),
            # 11: LeftFoot
            JointNode(11, "LeftFoot", 10, (-0.2, 0.0, 0.1), (0.0, -0.5, 0.1)),
            # 12: RightThigh
            JointNode(12, "RightThigh", 0, (0.2, 1.0, 0.0), (0.2, 0.0, 0.0)),
            # 13: RightCalf
            JointNode(13, "RightCalf", 12, (0.2, 0.5, 0.0), (0.0, -0.5, 0.0)),
            # 14: RightFoot
            JointNode(14, "RightFoot", 13, (0.2, 0.0, 0.1), (0.0, -0.5, 0.1)),
        ]
        # 填充子节点列表
        for j in joints:
            if j.parent_id is not None:
                joints[j.parent_id].children.append(j.joint_id)
        return joints

# -----------------------------------------------------------------------------
# 蒙皮权重分配器
# -----------------------------------------------------------------------------
class SkinWeightCalculator:
    @staticmethod
    def assign_weights(positions: List[float], joints: List[JointNode]) -> Tuple[List[int], List[float]]:
        """为顶点数组分配骨骼索引 (JOINTS_0, 4个ushort) 与 权重 (WEIGHTS_0, 4个float)"""
        vertex_count = len(positions) // 3
        joints_0 = []
        weights_0 = []

        for i in range(vertex_count):
            vx = positions[i * 3]
            vy = positions[i * 3 + 1]
            vz = positions[i * 3 + 2]

            # 计算顶点与每个骨骼节点的欧氏距离
            dists = []
            for j in joints:
                dx = vx - j.world_pos[0]
                dy = vy - j.world_pos[1]
                dz = vz - j.world_pos[2]
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                dists.append((dist, j.joint_id))

            dists.sort(key=lambda x: x[0])
            # 取最近的 2 个骨骼
            j0 = dists[0][1]
            j1 = dists[1][1]
            d0 = max(0.001, dists[0][0])
            d1 = max(0.001, dists[1][0])

            # 倒数距离权重
            w0 = 1.0 / (d0 * d0)
            w1 = 1.0 / (d1 * d1)
            total = w0 + w1
            w0 /= total
            w1 /= total

            joints_0.extend([j0, j1, 0, 0])
            weights_0.extend([round(w0, 4), round(w1, 4), 0.0, 0.0])

        return joints_0, weights_0

# -----------------------------------------------------------------------------
# 关键帧动画构建器
# -----------------------------------------------------------------------------
class AnimationTrackBuilder:
    @staticmethod
    def build_humanoid_clips(joints: List[JointNode]) -> List[AnimationClip]:
        """构建待机 (Idle)、行走 (Walk) 与攻击 (Attack) 三大标准动画剪辑"""
        clips = []

        # 1. Idle 呼吸动画 (2.0s 循环)
        idle_tracks = []
        times = [0.0, 1.0, 2.0]
        q_norm = (0.0, 0.0, 0.0, 1.0)
        q_breathe = quat_from_euler(math.radians(3.0), 0.0, 0.0)
        idle_tracks.append(KeyframeTrack(
            node_index=2, # Chest
            property_path="rotation",
            timestamps=times,
            values=[*q_norm, *q_breathe, *q_norm]
        ))
        q_head = quat_from_euler(math.radians(-2.0), 0.0, 0.0)
        idle_tracks.append(KeyframeTrack(
            node_index=4, # Head
            property_path="rotation",
            timestamps=times,
            values=[*q_norm, *q_head, *q_norm]
        ))
        clips.append(AnimationClip(name="Idle", duration=2.0, tracks=idle_tracks))

        # 2. Walk 循环对偶步伐 (1.2s 循环)
        walk_tracks = []
        w_times = [0.0, 0.3, 0.6, 0.9, 1.2]
        deg25 = math.radians(25.0)
        q_l_fwd = quat_from_euler(deg25, 0.0, 0.0)
        q_l_back = quat_from_euler(-deg25, 0.0, 0.0)
        walk_tracks.append(KeyframeTrack(
            node_index=9, # LeftThigh
            property_path="rotation",
            timestamps=w_times,
            values=[*q_norm, *q_l_fwd, *q_norm, *q_l_back, *q_norm]
        ))
        walk_tracks.append(KeyframeTrack(
            node_index=12, # RightThigh
            property_path="rotation",
            timestamps=w_times,
            values=[*q_norm, *q_l_back, *q_norm, *q_l_fwd, *q_norm]
        ))
        deg20 = math.radians(20.0)
        q_arm_fwd = quat_from_euler(deg20, 0.0, 0.0)
        q_arm_back = quat_from_euler(-deg20, 0.0, 0.0)
        walk_tracks.append(KeyframeTrack(
            node_index=5, # LeftUpperArm
            property_path="rotation",
            timestamps=w_times,
            values=[*q_norm, *q_arm_back, *q_norm, *q_arm_fwd, *q_norm]
        ))
        walk_tracks.append(KeyframeTrack(
            node_index=7, # RightUpperArm
            property_path="rotation",
            timestamps=w_times,
            values=[*q_norm, *q_arm_fwd, *q_norm, *q_arm_back, *q_norm]
        ))
        clips.append(AnimationClip(name="Walk", duration=1.2, tracks=walk_tracks))

        # 3. Attack 蓄力劈砍 (0.8s)
        atk_tracks = []
        a_times = [0.0, 0.25, 0.45, 0.8]
        q_windup = quat_from_euler(math.radians(-75.0), math.radians(15.0), 0.0)
        q_slash = quat_from_euler(math.radians(60.0), math.radians(-25.0), 0.0)
        atk_tracks.append(KeyframeTrack(
            node_index=7, # RightUpperArm
            property_path="rotation",
            timestamps=a_times,
            values=[*q_norm, *q_windup, *q_slash, *q_norm]
        ))
        q_torso = quat_from_euler(math.radians(12.0), math.radians(-10.0), 0.0)
        atk_tracks.append(KeyframeTrack(
            node_index=1, # Spine
            property_path="rotation",
            timestamps=a_times,
            values=[*q_norm, *q_norm, *q_torso, *q_norm]
        ))
        clips.append(AnimationClip(name="Attack", duration=0.8, tracks=atk_tracks))

        return clips

# -----------------------------------------------------------------------------
# 工业级 glTF 2.0 骨骼蒙皮动画导出器
# -----------------------------------------------------------------------------
class GLTFSkinExporter:
    @staticmethod
    def export(mesh_name: str,
               positions: List[float],
               normals: List[float],
               uvs: List[float],
               indices: List[int],
               joints: List[JointNode],
               clips: List[AnimationClip],
               output_path: Path) -> str:
        """导出完全符合 Khronos glTF 2.0 规范的带骨骼与动画的模型文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        joints_0, weights_0 = SkinWeightCalculator.assign_weights(positions, joints)

        bin_data = bytearray()
        buffer_views = []
        accessors = []

        def append_buffer(data_bytes: bytes, target: Optional[int] = None) -> int:
            nonlocal bin_data
            offset = len(bin_data)
            pad = (4 - (offset % 4)) % 4
            bin_data.extend(b'\x00' * pad)
            offset = len(bin_data)
            bin_data.extend(data_bytes)
            view_idx = len(buffer_views)
            bv = {
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": len(data_bytes)
            }
            if target:
                bv["target"] = target
            buffer_views.append(bv)
            return view_idx

        pos_bytes = struct.pack(f"<{len(positions)}f", *positions)
        bv_pos = append_buffer(pos_bytes, 34962)
        min_p = [min(positions[i::3]) for i in range(3)]
        max_p = [max(positions[i::3]) for i in range(3)]
        acc_pos = len(accessors)
        accessors.append({
            "bufferView": bv_pos,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(positions) // 3,
            "type": "VEC3",
            "max": max_p,
            "min": min_p
        })

        nor_bytes = struct.pack(f"<{len(normals)}f", *normals)
        bv_nor = append_buffer(nor_bytes, 34962)
        acc_nor = len(accessors)
        accessors.append({
            "bufferView": bv_nor,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(normals) // 3,
            "type": "VEC3"
        })

        uv_bytes = struct.pack(f"<{len(uvs)}f", *uvs)
        bv_uv = append_buffer(uv_bytes, 34962)
        acc_uv = len(accessors)
        accessors.append({
            "bufferView": bv_uv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(uvs) // 2,
            "type": "VEC2"
        })

        idx_bytes = struct.pack(f"<{len(indices)}H", *indices)
        bv_idx = append_buffer(idx_bytes, 34963)
        acc_idx = len(accessors)
        accessors.append({
            "bufferView": bv_idx,
            "byteOffset": 0,
            "componentType": 5123,
            "count": len(indices),
            "type": "SCALAR"
        })

        j_bytes = struct.pack(f"<{len(joints_0)}H", *joints_0)
        bv_j = append_buffer(j_bytes, 34962)
        acc_j = len(accessors)
        accessors.append({
            "bufferView": bv_j,
            "byteOffset": 0,
            "componentType": 5123,
            "count": len(joints_0) // 4,
            "type": "VEC4"
        })

        w_bytes = struct.pack(f"<{len(weights_0)}f", *weights_0)
        bv_w = append_buffer(w_bytes, 34962)
        acc_w = len(accessors)
        accessors.append({
            "bufferView": bv_w,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(weights_0) // 4,
            "type": "VEC4"
        })

        ibm_data = []
        for j in joints:
            ibm = translation_mat4(-j.world_pos[0], -j.world_pos[1], -j.world_pos[2])
            ibm_data.extend(ibm)
        ibm_bytes = struct.pack(f"<{len(ibm_data)}f", *ibm_data)
        bv_ibm = append_buffer(ibm_bytes)
        acc_ibm = len(accessors)
        accessors.append({
            "bufferView": bv_ibm,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(joints),
            "type": "MAT4"
        })

        mesh_node_idx = 0
        joint_node_offset = 1
        nodes = []
        nodes.append({
            "name": mesh_name,
            "mesh": 0,
            "skin": 0
        })
        for j in joints:
            n: Dict[str, Any] = {
                "name": j.name,
                "translation": list(j.local_translation),
                "rotation": list(j.local_rotation)
            }
            if j.children:
                n["children"] = [c + joint_node_offset for c in j.children]
            nodes.append(n)

        animations_json = []
        for clip in clips:
            samplers = []
            channels = []
            for track in clip.tracks:
                t_bytes = struct.pack(f"<{len(track.timestamps)}f", *track.timestamps)
                bv_t = append_buffer(t_bytes)
                acc_t = len(accessors)
                accessors.append({
                    "bufferView": bv_t,
                    "byteOffset": 0,
                    "componentType": 5126,
                    "count": len(track.timestamps),
                    "type": "SCALAR",
                    "min": [min(track.timestamps)],
                    "max": [max(track.timestamps)]
                })

                val_type = "VEC4" if track.property_path == "rotation" else "VEC3"
                val_bytes = struct.pack(f"<{len(track.values)}f", *track.values)
                bv_val = append_buffer(val_bytes)
                acc_val = len(accessors)
                accessors.append({
                    "bufferView": bv_val,
                    "byteOffset": 0,
                    "componentType": 5126,
                    "count": len(track.timestamps),
                    "type": val_type
                })

                sampler_idx = len(samplers)
                samplers.append({
                    "input": acc_t,
                    "interpolation": "LINEAR",
                    "output": acc_val
                })

                channels.append({
                    "sampler": sampler_idx,
                    "target": {
                        "node": track.node_index + joint_node_offset,
                        "path": track.property_path
                    }
                })

            animations_json.append({
                "name": clip.name,
                "samplers": samplers,
                "channels": channels
            })

        b64_uri = "data:application/octet-stream;base64," + base64.b64encode(bin_data).decode('ascii')
        gltf_doc = {
            "asset": {
                "version": "2.0",
                "generator": "Game-Agent SkeletalAnimationEngine v7.0"
            },
            "scene": 0,
            "scenes": [
                {
                    "nodes": [mesh_node_idx, joint_node_offset]
                }
            ],
            "nodes": nodes,
            "meshes": [
                {
                    "name": mesh_name,
                    "primitives": [
                        {
                            "attributes": {
                                "POSITION": acc_pos,
                                "NORMAL": acc_nor,
                                "TEXCOORD_0": acc_uv,
                                "JOINTS_0": acc_j,
                                "WEIGHTS_0": acc_w
                            },
                            "indices": acc_idx,
                            "material": 0
                        }
                    ]
                }
            ],
            "materials": [
                {
                    "name": "Warrior_PBR",
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [0.3, 0.6, 0.9, 1.0],
                        "metallicFactor": 0.7,
                        "roughnessFactor": 0.3
                    },
                    "emissiveFactor": [0.0, 0.2, 0.4],
                    "doubleSided": True
                }
            ],
            "skins": [
                {
                    "name": f"{mesh_name}_Armature",
                    "inverseBindMatrices": acc_ibm,
                    "joints": [i + joint_node_offset for i in range(len(joints))],
                    "skeleton": joint_node_offset
                }
            ],
            "animations": animations_json,
            "accessors": accessors,
            "bufferViews": buffer_views,
            "buffers": [
                {
                    "byteLength": len(bin_data),
                    "uri": b64_uri
                }
            ]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(gltf_doc, f, indent=2)

        return str(output_path)

# -----------------------------------------------------------------------------
# 顶层门面方法与程序化带骨骼机甲生成
# -----------------------------------------------------------------------------
class SkeletalAnimationEngine:
    @staticmethod
    def build_rigged_humanoid(output_file: Optional[str] = None) -> Dict[str, Any]:
        """程序化构建人形装甲战士模型与完整骨骼绑定和 3 套动画"""
        out_path = Path(output_file) if output_file else ROOT / "output" / "assets" / "3d" / "HeroRigged.gltf"

        positions = []
        normals = []
        uvs = []
        indices = []

        def add_box(center: Tuple[float, float, float], size: Tuple[float, float, float]):
            cx, cy, cz = center
            sx, sy, sz = size[0]*0.5, size[1]*0.5, size[2]*0.5
            corners = [
                (cx-sx, cy-sy, cz+sz), (cx+sx, cy-sy, cz+sz), (cx+sx, cy+sy, cz+sz), (cx-sx, cy+sy, cz+sz),
                (cx-sx, cy-sy, cz-sz), (cx+sx, cy-sy, cz-sz), (cx+sx, cy+sy, cz-sz), (cx-sx, cy+sy, cz-sz)
            ]
            faces = [
                ([0, 1, 2, 3], (0, 0, 1)),   # Front
                ([5, 4, 7, 6], (0, 0, -1)),  # Back
                ([4, 0, 3, 7], (-1, 0, 0)),  # Left
                ([1, 5, 6, 2], (1, 0, 0)),   # Right
                ([3, 2, 6, 7], (0, 1, 0)),   # Top
                ([4, 5, 1, 0], (0, -1, 0))   # Bottom
            ]
            for f_idx, n in faces:
                b = len(positions) // 3
                for c_i in f_idx:
                    positions.extend(corners[c_i])
                    normals.extend(n)
                    uvs.extend([0.0, 0.0])
                indices.extend([b, b+1, b+2, b, b+2, b+3])

        add_box((0.0, 1.3, 0.0), (0.5, 0.6, 0.3))
        add_box((0.0, 1.9, 0.0), (0.28, 0.28, 0.28))
        add_box((-0.5, 1.5, 0.0), (0.16, 0.5, 0.16))
        add_box((0.5, 1.5, 0.0), (0.16, 0.5, 0.16))
        add_box((-0.2, 0.5, 0.0), (0.18, 0.9, 0.18))
        add_box((0.2, 0.5, 0.0), (0.18, 0.9, 0.18))

        joints = JointHierarchy.create_humanoid_skeleton()
        clips = AnimationTrackBuilder.build_humanoid_clips(joints)

        filepath = GLTFSkinExporter.export(
            mesh_name="HeroRigged",
            positions=positions,
            normals=normals,
            uvs=uvs,
            indices=indices,
            joints=joints,
            clips=clips,
            output_path=out_path
        )

        return {
            "status": "SUCCESS",
            "model_name": "HeroRigged",
            "vertex_count": len(positions) // 3,
            "triangle_count": len(indices) // 3,
            "joint_count": len(joints),
            "animations": [c.name for c in clips],
            "filepath": filepath
        }

if __name__ == "__main__":
    res = SkeletalAnimationEngine.build_rigged_humanoid()
    print("SkeletalAnimationEngine 测试就绪:", res)
