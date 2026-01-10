import pandas as pd
import numpy as np
import joblib
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, precision_recall_curve, auc

print("✅ STEP 0: Script started")

# === 1. Load Dataset ===
features_path = "data/elliptic_txs_features.csv"
labels_path = "data/elliptic_txs_classes.csv"

print("📥 STEP 1: Loading CSVs...")

try:
    features_df = pd.read_csv(features_path, header=None)
    labels_df = pd.read_csv(labels_path, header=None)
except Exception as e:
    print(f"❌ ERROR loading CSV files: {e}")
    exit()

print("✅ STEP 2: CSVs loaded")

# Add column names
features_df.columns = ['tx_id'] + [f'f{i}' for i in range(1, 166)] + ['time_step']
labels_df.columns = ['tx_id', 'class']

features_df['tx_id'] = features_df['tx_id'].astype(str)
labels_df['tx_id'] = labels_df['tx_id'].astype(str)


# Merge & filter out 'unknown' classes
df = pd.merge(features_df, labels_df, on='tx_id')
df = df[df['class'] != 'unknown'].copy()
df['label'] = df['class'].map({'1': 1, '2': 0}).astype(int)

print("\n✅ 查看每個 time_step 有多少筆已標記的資料：")
print(df.groupby("time_step")["label"].count())
print("✅ STEP 3: Preprocessing done")

# === 2. Time-based split
# 排序所有唯一的 time_step（從小到大）
unique_steps = sorted(df['time_step'].unique())

# 使用前 80% 做訓練，後 20% 做測試
split_index = int(len(unique_steps) * 0.8)
train_steps = unique_steps[:split_index]
test_steps = unique_steps[split_index:]

train_df = df[df['time_step'].isin(train_steps)]
test_df = df[df['time_step'].isin(test_steps)]


drop_cols = ['tx_id', 'time_step', 'class', 'label']
X_train = train_df.drop(columns=drop_cols)
y_train = train_df['label']
X_test = test_df.drop(columns=drop_cols)
y_test = test_df['label']

print("✅ STEP 4: Train/test split done")

# === 3. Handle class imbalance ===
pos = sum(y_train == 1)
neg = sum(y_train == 0)
scale = neg / pos
print(f"📊 STEP 5: Class balance scale = {scale:.2f}")

# === 4. Train model ===
print("🧠 STEP 6: Training model...")
print(f"Train set size: {len(y_train)}")
print(f"Test set size: {len(y_test)}")
model = XGBClassifier(use_label_encoder=False, eval_metric='logloss',
                      scale_pos_weight=scale, random_state=42)
model.fit(X_train, y_train)

print("✅ STEP 7: Model trained")

# === 5. Evaluate model ===
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred, labels=[0, 1], target_names=["Licit", "Illicit"]))


roc = roc_auc_score(y_test, y_prob)
precision, recall, _ = precision_recall_curve(y_test, y_prob)
pr_auc = auc(recall, precision)

print(f"ROC-AUC: {roc:.4f}")
print(f"PR-AUC : {pr_auc:.4f}")
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# === 6. Save model ===
output_path = "backend/app/models/xgboost_aml_model.pkl"
joblib.dump(model, output_path)
print(f"✅ STEP 8: Model saved to {output_path}")
