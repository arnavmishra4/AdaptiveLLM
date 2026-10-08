import os

from openai import OpenAI

from router_app.Router import route


client = OpenAI(
    base_url="http://192.168.1.6:4000",
    api_key=os.environ.get("LITELLM_API_KEY", "local-dev-key"),
)

messages = []
while True:
    user_input = input("You: ")
    model_router = route(user_input)
    if user_input.lower() in ["exit", "quit"]:
        print("conversation ended.")
        break

    messages.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model=model_router,
        messages=messages,
    )
    assistant_message = response.choices[0].message.content

    messages.append({"role": "assistant", "content": assistant_message})
    print(f"Assistant: {assistant_message}")