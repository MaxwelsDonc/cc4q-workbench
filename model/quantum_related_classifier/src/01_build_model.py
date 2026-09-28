import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
sys.path.append(PROJECT_ROOT)
from transformers import BertForSequenceClassification, BertTokenizer, Trainer, TrainingArguments
from datasets import load_dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from loguru import logger
logger.add('model/quantum_related_classifier/log/01_build_model.log', rotation='1 day', retention='7 days', compression='zip')

def download_bert_model(model_path=os.path.join(PROJECT_ROOT, 'model/BERT/BERT_downloaded')):
    logger.info(f'PROJECT_ROOT: {PROJECT_ROOT}')
    logger.info(f'正在从本地路径加载模型: {model_path}')
    tokenizer = BertTokenizer.from_pretrained(model_path)
    model = BertForSequenceClassification.from_pretrained(model_path, num_labels=2)
    logger.info('BERT 模型和分词器已成功从本地离线加载。')
    return (tokenizer, model)

def load_and_preprocess_data(file_path, tokenizer, max_length=512, test_size=0.2, val_size=0.1):
    logger.info(f'加载数据文件：{file_path}')
    dataset = load_dataset('json', data_files={'data': file_path})
    split_dataset = dataset['data'].train_test_split(test_size=test_size)
    train_val_split = split_dataset['train'].train_test_split(test_size=val_size)

    def preprocess_function(examples):
        tokenized = tokenizer(examples['comment'], padding='max_length', truncation=True, max_length=max_length)
        return tokenized
    tokenized_train_dataset = train_val_split['train'].map(preprocess_function, batched=True)
    tokenized_val_dataset = train_val_split['test'].map(preprocess_function, batched=True)
    tokenized_test_dataset = split_dataset['test'].map(preprocess_function, batched=True)
    logger.info(f'数据预处理完成，训练集大小: {len(tokenized_train_dataset)}, 验证集大小: {len(tokenized_val_dataset)}, 测试集大小: {len(tokenized_test_dataset)}')
    return (tokenized_train_dataset, tokenized_val_dataset, tokenized_test_dataset)

def compute_metrics(p):
    preds, labels = p
    preds = preds.argmax(axis=1)
    accuracy = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='binary')
    return {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1}

def train_model(model, train_dataset, val_dataset, output_dir=os.path.join(PROJECT_ROOT, 'model/quantum_related_classifier/BERT_QR_classifier'), batch_size=16, epochs=5):
    logger.info(f'开始训练模型，训练集大小: {len(train_dataset)}, 验证集大小: {len(val_dataset)}')
    training_args = TrainingArguments(output_dir=output_dir, eval_strategy='epoch', save_strategy='epoch', learning_rate=2e-05, per_device_train_batch_size=batch_size, per_device_eval_batch_size=batch_size, num_train_epochs=epochs, weight_decay=0.01, logging_dir=output_dir, logging_steps=10, load_best_model_at_end=True, metric_for_best_model='f1', save_total_limit=2)
    trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset, eval_dataset=val_dataset, compute_metrics=compute_metrics)
    logger.info(f'使用设备: {trainer.args.device}')
    trainer.train()
    logger.info('训练完成。')
    return trainer
if __name__ == '__main__':
    MODEL_DIR = 'bert-base-uncased'
    OUT_DIR = os.path.join(PROJECT_ROOT, 'model/quantum_related_classifier/BERT_QR_classifier')
    logger.info('下载BERT模型和分词器...')
    tokenizer, model = download_bert_model(MODEL_DIR)
    logger.info('加载并处理数据...')
    train_data, val_data, test_data = load_and_preprocess_data(os.path.join(PROJECT_ROOT, 'model/quantum_related_classifier/data/train/all_data.jsonl'), tokenizer)
    trainer = train_model(model=model, train_dataset=train_data, val_dataset=val_data, output_dir=os.path.join(OUT_DIR, 'checkpoint'), batch_size=32, epochs=30)
    logger.info('在测试集上评估模型...')
    results = trainer.evaluate(test_data)
    logger.info(f'评估结果: {results}')
    logger.info(f'最好的模型保存路径: {trainer.state.best_model_checkpoint}')
    logger.info('保存最终模型和分词器到输出目录...')
    trainer.save_model(os.path.join(OUT_DIR, 'saved_model'))
    tokenizer.save_pretrained(os.path.join(OUT_DIR, 'saved_model'))
