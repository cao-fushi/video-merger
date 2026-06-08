"""配置管理模块 - 保存和加载用户配置"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".video_merger")
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.json")

# 默认配置
DEFAULT_CONFIG = {
    "合成配置": {
        "每组片段数": 2,
        "开头模式": 0,  # 0: 轮流, 1: 指定, 2: 随机
        "合成数量模式": 0,  # 0: 全部, 1: 自定义
        "自定义数量": 100,
        "文件前缀": "合成视频"
    },
    "预处理配置": {
        "统一分辨率": False,
        "分辨率": "1080x1920",
        "统一帧率": False,
        "帧率": 30,
        "编码器": 0,  # 0: H.264, 1: H.265
        "质量": 1,  # 0: 高, 1: 中, 2: 低
        "硬件加速": 0  # 0: 自动, 1: NVENC, 2: CPU
    },
    "转场配置": {
        "转场类型": 0,  # 0: 无, 1-14: 各种转场
        "转场时长": 0.5
    },
    "音频配置": {
        "音频淡入淡出": True,
        "淡入淡出时长": 0.5
    },
    "性能配置": {
        "并行线程数": 2,
        "覆盖已存在文件": True
    },
    "路径配置": {
        "输出目录": "",
        "上次导入目录": ""
    }
}


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，默认使用用户目录下的配置
        """
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置（处理新增的配置项）
                return self._merge_config(DEFAULT_CONFIG, config)
            else:
                logger.info(f"配置文件不存在，使用默认配置: {self.config_file}")
                return DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return DEFAULT_CONFIG.copy()

    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """合并默认配置和用户配置"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)

            logger.info(f"配置已保存: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def get(self, section: str, key: str, default=None) -> Any:
        """获取配置值"""
        try:
            return self.config.get(section, {}).get(key, default)
        except:
            return default

    def set(self, section: str, key: str, value: Any) -> None:
        """设置配置值"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config.copy()

    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config = DEFAULT_CONFIG.copy()
        self.save_config()

    def update_from_gui(self, gui_data: Dict[str, Any]) -> None:
        """从GUI数据更新配置"""
        try:
            # 合成配置
            if "合成配置" in gui_data:
                self.config["合成配置"].update(gui_data["合成配置"])

            # 预处理配置
            if "预处理配置" in gui_data:
                self.config["预处理配置"].update(gui_data["预处理配置"])

            # 转场配置
            if "转场配置" in gui_data:
                self.config["转场配置"].update(gui_data["转场配置"])

            # 音频配置
            if "音频配置" in gui_data:
                self.config["音频配置"].update(gui_data["音频配置"])

            # 性能配置
            if "性能配置" in gui_data:
                self.config["性能配置"].update(gui_data["性能配置"])

            # 路径配置
            if "路径配置" in gui_data:
                self.config["路径配置"].update(gui_data["路径配置"])

            self.save_config()
        except Exception as e:
            logger.error(f"更新配置失败: {e}")

    def to_gui_data(self) -> Dict[str, Any]:
        """转换为GUI数据格式"""
        return self.config.copy()


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
