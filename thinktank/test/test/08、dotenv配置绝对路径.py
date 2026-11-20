# 使用绝对路径加载 .env
import os

from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(dotenv_path=env_path, override=True)

if __name__ == '__main__':

    print(os.path.dirname(__file__))
    # print(os.path.join(os.path.dirname(__file__), "../../.env"))
    # print(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env")))