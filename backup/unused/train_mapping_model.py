"""
train_mapping_model.py — Fine-tune a small model for IPC→BNS mapping
"""

import json
import os
from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
import torch
from datasets import Dataset

class IPCMappingDataset:
    def __init__(self, mappings_file: str = None):
        self.mappings_file = mappings_file or os.path.join(
            os.path.dirname(__file__), 
            "ipc_bns_mappings.json"
        )
        self.mappings = self.load_mappings()
        self.samples = self.create_samples()
    
    def load_mappings(self) -> Dict:
        """Load the dynamic mappings from JSON"""
        with open(self.mappings_file, 'r') as f:
            return json.load(f)
    
    def create_samples(self) -> List[Dict]:
        """Create training samples from mappings"""
        samples = []
        
        for ipc_ref, mapping in self.mappings.items():
            # Create variations of the same reference
            variations = [
                ipc_ref,
                f"Section {ipc_ref.split()[1]}",
                f"Sec. {ipc_ref.split()[1]}",
                f"{ipc_ref.split()[1]} IPC",
            ]
            
            for text in variations:
                samples.append({
                    "text": text,
                    "label": mapping["bns"],
                    "description": mapping["name"]
                })
        
        return samples

def train_model():
    """Fine-tune a small BERT model for section mapping"""
    # Load dataset
    dataset = IPCMappingDataset()
    
    # Convert to HuggingFace Dataset
    hf_dataset = Dataset.from_list(dataset.samples)
    
    # Tokenize
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)
    
    tokenized_dataset = hf_dataset.map(tokenize_function, batched=True)
    
    # Create label mapping
    unique_labels = list(set(s["label"] for s in dataset.samples))
    label_to_id = {label: i for i, label in enumerate(unique_labels)}
    
    def add_labels(examples):
        examples["labels"] = [label_to_id[label] for label in examples["label"]]
        return examples
    
    tokenized_dataset = tokenized_dataset.map(add_labels, batched=True)
    
    # Load model
    model = AutoModelForSequenceClassification.from_pretrained(
        "bert-base-uncased",
        num_labels=len(unique_labels)
    )
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir="./ipc_bns_mapping_model",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir="./logs",
        save_steps=500,
        save_total_limit=2,
    )
    
    # Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        tokenizer=tokenizer,
    )
    
    trainer.train()
    
    # Save model
    model.save_pretrained("./ipc_bns_mapping_model")
    tokenizer.save_pretrained("./ipc_bns_mapping_model")
    
    print(f"Model trained on {len(dataset.samples)} samples")
    return model, tokenizer, label_to_id

if __name__ == "__main__":
    train_model()