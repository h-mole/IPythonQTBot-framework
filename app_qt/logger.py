import logging
import sys
from rich.logging import RichHandler

# 要求logging能够打印出Logger name，所在文件和行号、日期时间以及日志内容
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    # stream=sys.stdout,
    handlers=[RichHandler()],
)
system_logger = logging.getLogger(__name__)
