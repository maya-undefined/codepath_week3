from dotenv import load_dotenv
import chainlit as cl

load_dotenv()

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
# from langsmith.wrappers import wrap_openai
# from langsmith import traceable
# client = wrap_openai(openai.AsyncClient())

from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI

from movie_functions import get_now_playing_movies, get_showtimes

client = AsyncOpenAI()

gen_kwargs = {
    "model": "gpt-4o",
    "temperature": 0.2,
    "max_tokens": 500
}

SYSTEM_PROMPT = """\
You are a helpful movie assistant. In addition to talking about movies 
like you are Cramar like in that one episode of Seifeld, you can also 
call these functions

In addition you should detect when a user wants to do what these 
functions ask and generate a function call with parameters filled 
in and for them with no other comment

The list of functions are listed below

def get_now_playing_movies()
def get_showtimes(title, location)
def buy_ticket(theater, movie, showtime)
def get_reviews(movie_id)

functions with parameters should list out their arguments after the function name, such as this
foo() bar baz

if foo took two parameters bar and baz

"""

@observe
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@observe
async def generate_response(client, message_history, gen_kwargs):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)
    
    await response_message.update()

    return response_message

@cl.on_message
@observe
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = await generate_response(client, message_history, gen_kwargs)

    if "get_now_playing_movies" in response_message.content:
        movies = get_now_playing_movies()
        await cl.Message(content=movies).send()
        message_history.append({"role": "assistant", "content":movies})
    elif "get_showtimes" in response_message.content:
        movies = eval(response_message.content)
        await cl.Message(content=movies).send()
        message_history.append({"role": "assistant", "content":movies})        
    elif buy_ticket in response_message.content:
        pass
    elif get_reviews in response_message.content:
        pass        
    else:
        message_history.append({"role": "assistant", "content": response_message.content})

    cl.user_session.set("message_history", message_history)

if __name__ == "__main__":
    cl.main()
