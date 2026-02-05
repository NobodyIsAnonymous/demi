import json
from openai import OpenAI

client = OpenAI()  # 默认从环境变量里拿 OPENAI_API_KEY

# 1. 上传训练文件
train_file = client.files.create(
    file=open("train.jsonl", "rb"),
    purpose="fine-tune"
)

print("Uploaded file id:", train_file.id)

# 2. 创建 fine-tuning 任务（以 gpt-4o-mini 为例）
job = client.fine_tuning.jobs.create(
    model="gpt-4o-mini-2024-07-18",
    training_file=train_file.id,
    # 可选参数:
    # validation_file=...,
    # hyperparameters={"n_epochs": 3}
)

print("Fine-tuning job id:", job.id)

# 3. （可选）轮询查看训练状态
job = client.fine_tuning.jobs.retrieve(job.id)
print("Status:", job.status)

# 当 status == "succeeded" 时，你可以拿到 fine-tuned 模型名:
print("Fine-tuned model:", job.fine_tuned_model)