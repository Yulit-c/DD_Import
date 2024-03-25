"""----------------------------------------------------
# Logger の設定
-----------------------------------------------------"""
from .Logging.preparation_logger import preparating_logger

logger = preparating_logger(__name__)
#######################################################


def launch_debug_server():
    logger.debug("Begin Launch Debug Server Processing")
    import ptvsd

    # デバッグサーバの立ち上げ
    # IPアドレス0.0.0.0（ローカルホスト）、ポート5678として立ち上げる
    ptvsd.enable_attach(address=("0.0.0.0", 5678))
    # Visual Studio Codeからのデバッグリクエストを待ち受ける
    ptvsd.wait_for_attach()
