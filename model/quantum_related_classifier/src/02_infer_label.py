import os
import json
from transformers import BertForSequenceClassification, BertTokenizer
from datasets import load_dataset
from sklearn.metrics import classification_report, accuracy_score
import torch
from loguru import logger
logger.add('model/quantum_related_classifier/log/02_infer_label.log', rotation='1 day', retention='7 days')

def load_model_and_tokenizer(model_dir):
    tokenizer = BertTokenizer.from_pretrained(model_dir)
    model = BertForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    return (tokenizer, model)

def predict(model, tokenizer, texts, batch_size=32, device='cpu'):
    all_preds = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        inputs = tokenizer(batch_texts, return_tensors='pt', padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.inference_mode():
            outputs = model(**inputs)
            logits = outputs.logits
            preds = logits.argmax(dim=1).cpu().tolist()
            all_preds.extend(preds)
    return all_preds

def evaluate(model_dir, test_file):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f'使用设备：{device}')
    tokenizer, model = load_model_and_tokenizer(model_dir)
    model.to(device)
    logger.info(f'加载测试数据：{test_file}')
    dataset = load_dataset('json', data_files={'test': test_file})
    test_data = dataset['test']
    texts = test_data['comment']
    labels = test_data['label']
    logger.info(f'测试样本数量：{len(texts)}')
    preds = predict(model, tokenizer, texts, device=device)
    acc = accuracy_score(labels, preds)
    report = classification_report(labels, preds, digits=4)
    logger.info(f'准确率：{acc}')
    logger.info(f'\n分类报告：\n{report}')

def classify_and_split_data(model_dir, source_file, out_dir):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f'使用设备：{device}')
    tokenizer, model = load_model_and_tokenizer(model_dir)
    model.to(device)
    logger.info(f'加载源数据：{source_file}')
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f'总数据量：{len(data)}')
    comment_texts = [item['comment_text'] for item in data]
    logger.info('开始进行分类预测...')
    predictions = predict(model, tokenizer, comment_texts, device=device)
    quantum_specific_data = []
    not_quantum_specific_data = []
    for i, pred in enumerate(predictions):
        if pred == 1:
            quantum_specific_data.append(data[i])
        else:
            not_quantum_specific_data.append(data[i])
    os.makedirs(out_dir, exist_ok=True)
    quantum_file = os.path.join(out_dir, 'quantum_related_r2.json')
    not_quantum_file = os.path.join(out_dir, 'not_quantum_related_r2.json')
    with open(quantum_file, 'w', encoding='utf-8') as f:
        json.dump(quantum_specific_data, f, ensure_ascii=False, indent=2)
    with open(not_quantum_file, 'w', encoding='utf-8') as f:
        json.dump(not_quantum_specific_data, f, ensure_ascii=False, indent=2)
    logger.info(f'分类完成！')
    logger.info(f'Quantum specific (标签=1): {len(quantum_specific_data)} 条')
    logger.info(f'Not quantum specific (标签=0): {len(not_quantum_specific_data)} 条')
    logger.info(f'结果已保存到：')
    logger.info(f'  - {quantum_file}')
    logger.info(f'  - {not_quantum_file}')
    return (len(quantum_specific_data), len(not_quantum_specific_data))
if __name__ == '__main__':
    MODEL_DIR = 'model/quantum_related_classifier/BERT_QR_classifier/saved_model'
    TEST_FILE = 'model/quantum_related_classifier/data/train/all_data.jsonl'
    SOURCE_FILE = 'model/quantum_related_classifier/data/infer/infer_data_r2.json'
    OUT_DIR = 'model/quantum_related_classifier/output/'
    evaluate(MODEL_DIR, TEST_FILE)
    classify_and_split_data(MODEL_DIR, SOURCE_FILE, OUT_DIR)
