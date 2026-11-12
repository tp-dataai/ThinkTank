from langchain.chat_models import init_chat_model
from thinktank.config.config import LLMConfig

llm_init = None

def get_llm_init():
    global llm_init

    if llm_init is None:
        llm = init_chat_model(
            model=LLMConfig.item_model,
            model_provider="openai",
            base_url=LLMConfig.openai_api_base,
            api_key=LLMConfig.openai_api_key,
            temperature=LLMConfig.llm_default_temperature
        )

    return llm

if __name__ =="__main__":
    llm = get_llm_init()
    print(llm)