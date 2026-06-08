"""排列组合生成模块 - 生成视频合成方案"""
import random
from itertools import permutations, combinations
from typing import List, Optional, Tuple
from .video_info import VideoInfo


def generate_combinations(
    videos: List[VideoInfo],
    group_size: int = 2,
    start_video: Optional[VideoInfo] = None,
    max_count: Optional[int] = None,
    allow_repeat: bool = False
) -> List[List[VideoInfo]]:
    """
    生成视频合成组合方案

    Args:
        videos: 视频列表
        group_size: 每组合成的视频数量
        start_video: 指定的开头视频，None表示不指定
        max_count: 最大合成数量，None表示全部
        allow_repeat: 是否允许同一视频在同一组合中重复出现

    Returns:
        合成方案列表，每个方案是一个VideoInfo列表
    """
    if not videos or group_size < 2:
        return []

    # 如果指定了开头视频
    if start_video:
        # 获取剩余视频（排除开头视频）
        remaining = [v for v in videos if v.视频路径 != start_video.视频路径]

        if not remaining:
            return []

        # 需要从剩余视频中选择 group_size - 1 个
        select_count = group_size - 1

        if select_count > len(remaining):
            # 如果剩余视频不够，使用所有剩余视频
            select_count = len(remaining)

        # 生成所有可能的排列组合
        all_combinations = []

        # 使用排列（考虑顺序）
        for perm in permutations(remaining, select_count):
            combo = [start_video] + list(perm)
            all_combinations.append(combo)

        # 如果需要限制数量
        if max_count and max_count < len(all_combinations):
            # 随机选择指定数量的组合
            all_combinations = random.sample(all_combinations, max_count)

        return all_combinations

    else:
        # 未指定开头视频，每个视频轮流作为开头
        all_combinations = []

        for start_vid in videos:
            remaining = [v for v in videos if v.视频路径 != start_vid.视频路径]

            if not remaining:
                continue

            select_count = group_size - 1

            if select_count > len(remaining):
                select_count = len(remaining)

            # 为当前开头视频生成组合
            for perm in permutations(remaining, select_count):
                combo = [start_vid] + list(perm)
                all_combinations.append(combo)

        # 如果需要限制数量
        if max_count and max_count < len(all_combinations):
            all_combinations = random.sample(all_combinations, max_count)

        return all_combinations


def generate_random_combinations(
    videos: List[VideoInfo],
    group_size: int = 2,
    count: int = 10,
    start_video: Optional[VideoInfo] = None
) -> List[List[VideoInfo]]:
    """
    生成随机视频合成组合

    Args:
        videos: 视频列表
        group_size: 每组合成的视频数量
        count: 生成数量
        start_video: 指定的开头视频

    Returns:
        合成方案列表
    """
    if not videos or group_size < 2 or count < 1:
        return []

    combinations_list = []

    for _ in range(count):
        if start_video:
            # 指定了开头视频
            remaining = [v for v in videos if v.视频路径 != start_video.视频路径]
            if not remaining:
                break

            select_count = min(group_size - 1, len(remaining))
            selected = random.sample(remaining, select_count)
            combo = [start_video] + selected
        else:
            # 随机选择开头视频
            if len(videos) < group_size:
                combo = random.sample(videos, len(videos))
            else:
                combo = random.sample(videos, group_size)

        combinations_list.append(combo)

    return combinations_list


def generate_sequential_combinations(
    videos: List[VideoInfo],
    group_size: int = 2,
    start_index: int = 0
) -> List[List[VideoInfo]]:
    """
    按顺序生成视频合成组合

    Args:
        videos: 视频列表
        group_size: 每组合成的视频数量
        start_index: 起始视频索引

    Returns:
        合成方案列表
    """
    if not videos or group_size < 2:
        return []

    combinations_list = []
    n = len(videos)

    # 确保起始索引有效
    start_index = start_index % n

    # 按顺序生成组合
    for i in range(n):
        # 计算当前开头视频的索引
        head_idx = (start_index + i) % n
        head_video = videos[head_idx]

        # 获取剩余视频（保持顺序）
        remaining = []
        for j in range(1, n):
            idx = (head_idx + j) % n
            remaining.append(videos[idx])

        # 选择 group_size - 1 个视频
        select_count = min(group_size - 1, len(remaining))
        selected = remaining[:select_count]

        combo = [head_video] + selected
        combinations_list.append(combo)

    return combinations_list


def estimate_combination_count(
    video_count: int,
    group_size: int,
    has_start_video: bool = False
) -> int:
    """
    估算组合数量

    Args:
        video_count: 视频总数
        group_size: 每组视频数
        has_start_video: 是否指定了开头视频

    Returns:
        预计组合数量
    """
    if video_count < 2 or group_size < 2:
        return 0

    if has_start_video:
        # 指定了开头视频，从剩余 n-1 个中选 group_size-1 个的排列
        remaining = video_count - 1
        select = group_size - 1
        if remaining < select:
            return 0
        # 排列数 P(remaining, select)
        result = 1
        for i in range(select):
            result *= (remaining - i)
        return result
    else:
        # 未指定开头，每个视频轮流开头
        remaining = video_count - 1
        select = group_size - 1
        if remaining < select:
            return 0
        # 每个开头视频的排列数
        perms_per_start = 1
        for i in range(select):
            perms_per_start *= (remaining - i)
        return perms_per_start * video_count
