"""自动撤回工具

提取 pic_action / pic_command 中重复的 ~60 行 recall_task 逻辑。
"""

import asyncio
import time as time_module
from typing import Callable, Awaitable, Any

from src.common.logger import get_logger

logger = get_logger("mais_art.recall")


async def schedule_auto_recall(
    chat_id: str,
    delay_seconds: int,
    log_prefix: str,
    send_command_fn: Callable[..., Awaitable[Any]],
):
    """安排消息自动撤回后台任务

    查询最近由 Bot 发送的消息，等待指定时间后尝试撤回。

    Args:
        chat_id: 聊天流 ID
        delay_seconds: 撤回延时（秒）
        log_prefix: 日志前缀
        send_command_fn: 发送平台命令的异步函数，
            签名: (command_name, args, storage_message) -> result
    """

    async def _recall_task():
        try:
            # 等待让消息存储和 echo 回调完成
            await asyncio.sleep(4)

            from src.plugin_system.apis import message_api
            from src.config.config import global_config

            current_time = time_module.time()
            messages = message_api.get_messages_by_time_in_chat(
                chat_id=chat_id,
                start_time=current_time - 10,
                end_time=current_time + 1,
                limit=5,
                limit_mode="latest",
            )

            bot_id = str(global_config.bot.qq_account)
            target_message_id = None

            for msg in messages:
                if str(msg.user_info.user_id) == bot_id:
                    mid = str(msg.message_id)
                    if mid.isdigit():
                        target_message_id = mid
                        break
                    else:
                        logger.debug(f"{log_prefix} 跳过非平台消息ID: {mid}")

            if not target_message_id:
                logger.warning(f"{log_prefix} 未找到有效的平台消息ID（需要纯数字格式）")
                return

            logger.info(
                f"{log_prefix} 安排消息自动撤回，延时: {delay_seconds}秒，消息ID: {target_message_id}"
            )

            await asyncio.sleep(delay_seconds)

            DELETE_COMMAND_CANDIDATES = [
                "DELETE_MSG",
                "delete_msg",
                "RECALL_MSG",
                "recall_msg",
            ]
            recall_success = False

            for cmd in DELETE_COMMAND_CANDIDATES:
                try:
                    result = await send_command_fn(
                        command_name=cmd,
                        args={"message_id": str(target_message_id)},
                        storage_message=False,
                    )
                    if isinstance(result, bool) and result:
                        recall_success = True
                        logger.info(
                            f"{log_prefix} 消息自动撤回成功，命令: {cmd}，消息ID: {target_message_id}"
                        )
                        break
                    elif isinstance(result, dict):
                        status = str(result.get("status", "")).lower()
                        if (
                            status in ("ok", "success")
                            or result.get("retcode") == 0
                            or result.get("code") == 0
                        ):
                            recall_success = True
                            logger.info(
                                f"{log_prefix} 消息自动撤回成功，命令: {cmd}，消息ID: {target_message_id}"
                            )
                            break
                except Exception as e:
                    logger.debug(f"{log_prefix} 撤回命令 {cmd} 失败: {e}")
                    continue

            if not recall_success:
                logger.warning(
                    f"{log_prefix} 消息自动撤回失败，消息ID: {target_message_id}，已尝试所有命令"
                )

        except asyncio.CancelledError:
            logger.debug(f"{log_prefix} 自动撤回任务被取消")
        except Exception as e:
            logger.error(f"{log_prefix} 自动撤回失败: {e}")

    asyncio.create_task(_recall_task())
