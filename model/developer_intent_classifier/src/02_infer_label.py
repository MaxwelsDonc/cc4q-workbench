import os
import json
from transformers import BertForSequenceClassification, BertTokenizer
import torch
from loguru import logger
logger.add('model/developer_intent_classifier/log/02_infer_label.log', rotation='1 day', retention='7 days', compression='zip')
INTENT_MAPPING = {0: 'What', 1: 'How-to-use', 2: 'How-it-is-done', 3: 'Property', 4: 'Why', 5: 'Others'}

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

def classify_ccps(model_dir, source_file, output_dir, file_suffix):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f'Using device: {device}')
    logger.info(f'Loading model: {model_dir}')
    tokenizer, model = load_model_and_tokenizer(model_dir)
    model.to(device)
    logger.info(f'Loading source data: {source_file}')
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f'Total records: {len(data)}')
    comment_texts = [item['comment_text'] for item in data]
    ids = [item['id'] for item in data]
    SDKs = [item['SDK'] for item in data]
    logger.info('Starting developer-intent classification...')
    predictions = predict(model, tokenizer, comment_texts, device=device)
    results = {}
    intent_counts = {intent: 0 for intent in INTENT_MAPPING.values()}
    for i, pred in enumerate(predictions):
        intent_label = INTENT_MAPPING[pred]
        results[i] = {'id': ids[i], 'SDK': SDKs[i], 'intent': intent_label}
        intent_counts[intent_label] += 1
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'task2_results_{file_suffix}_r2.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f'Classification finished!')
    logger.info(f'Results saved to: {output_file}')
    logger.info('Per-intent counts:')
    for intent, count in intent_counts.items():
        logger.info(f'  - {intent}: {count} records')
    return (results, intent_counts)
if __name__ == '__main__':
    MODEL_DIR = 'model/developer_intent_classifier/BERT_DI_classifier/saved_best_model'
    OUTPUT_DIR = 'model/developer_intent_classifier/output'
    SOURCE_FILES = [{'file': 'model/quantum_related_classifier/output/not_quantum_related_r2.json', 'suffix': 'quantum_not_related'}, {'file': 'model/quantum_related_classifier/output/quantum_related_r2.json', 'suffix': 'quantum_related'}]
    for source_info in SOURCE_FILES:
        logger.info(f"\nProcessing file: {source_info['file']}")
        results, counts = classify_ccps(MODEL_DIR, source_info['file'], OUTPUT_DIR, source_info['suffix'])
        logger.info(f"File {source_info['suffix']} done!\n")
    logger.info('All developer-intent classification tasks finished!')
