import copy
import torch
from prompt import system_prompt
from model import model , tokenizer
router_prompt = system_prompt  # already defined by you

# ---- Build and cache the static prefix once ----
prefix_messages = [{"role": "system", "content": router_prompt}]
prefix_ids = tokenizer.apply_chat_template(
    prefix_messages,
    add_generation_prompt=False,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

with torch.no_grad():
    prefix_out = model(prefix_ids["input_ids"], use_cache=True)
base_cache = prefix_out.past_key_values  # reusable KV cache


def route(user_input: str, max_new_tokens: int = 10) -> str:
    messages = [
        {"role": "system", "content": router_prompt},
        {"role": "user", "content": user_input},
    ]
    ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        enable_thinking=False,
    ).to(model.device)

    with torch.no_grad():
        output = model.generate(ids["input_ids"], max_new_tokens=max_new_tokens)

    return tokenizer.decode(
        output[0][ids["input_ids"].shape[-1]:], skip_special_tokens=True
    ).strip()


# ---- Test it ----
'''
print(route("My name is Arnav Mishra, what is the greatest book on this entire planet"))
print(route("Summarize this paragraph in one sentence: The economy grew by 3% last quarter."))
print(route("help me with this equation of the black hole"))

'''
