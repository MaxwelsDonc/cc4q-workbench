import os
import json
from transformers import BertForSequenceClassification, BertTokenizer
import torch
from loguru import logger
logger.add('model/quantum_category_classifier/log/02_infer_label.log', rotation='1 day', retention='7 days', compression='zip')
CATEGORY_MAPPING = {0: 'Mathematics for quantum information', 1: 'Quantum algorithms', 2: 'Quantum circuit model', 3: 'Quantum hardware', 4: 'Quantum software framework', 5: 'Others'}

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
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            preds = logits.argmax(dim=1).cpu().tolist()
            all_preds.extend(preds)
    return all_preds

def classify_ccps(model_dir, source_file, output_dir):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f'使用设备：{device}')
    logger.info(f'加载模型：{model_dir}')
    tokenizer, model = load_model_and_tokenizer(model_dir)
    model.to(device)
    logger.info(f'加载源数据：{source_file}')
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f'总数据量：{len(data)}')
    comment_texts = [item['comment_text'] for item in data]
    ids = [item['id'] for item in data]
    SDKs = [item['SDK'] for item in data]
    logger.info('开始进行分类预测...')
    predictions = predict(model, tokenizer, comment_texts, device=device)
    results = {}
    category_counts = {category: 0 for category in CATEGORY_MAPPING.values()}
    for i, pred in enumerate(predictions):
        category_label = CATEGORY_MAPPING[pred]
        results[i] = {'id': ids[i], 'SDK': SDKs[i], 'category': category_label}
        category_counts[category_label] += 1
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'task3_results_r2.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f'分类完成！')
    logger.info(f'结果已保存到：{output_file}')
    logger.info('各类别统计：')
    for category, count in category_counts.items():
        logger.info(f'  - {category}: {count} 条')
    return (results, category_counts)
if __name__ == '__main__':
    MODEL_DIR = 'model/quantum_category_classifier/BERT_QC_classifier/saved_best_model'
    SOURCE_FILE = 'model/quantum_related_classifier/output/quantum_related_r2.json'
    OUTPUT_DIR = 'model/quantum_category_classifier/output'
    results, counts = classify_ccps(MODEL_DIR, SOURCE_FILE, OUTPUT_DIR)
    logger.info('量子分类任务完成！')
