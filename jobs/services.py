from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
import json

from .models import Job
from .serializers import JobSerializer, JobListSerializer

import os
import time
from dotenv import load_dotenv
from groq import Groq
from django.conf import settings

load_dotenv()

class TransactionProcessor:
    def process(self, file):
        # print("process")
        df = self.load_csv(file)
        clean_df = self.data_cleaning(df)
        final_df = self.anomaly_detection(clean_df)
        final_df = self.llm_classification(final_df)
        summary = self.llm_summary(final_df)

        final_df['date'] = final_df['date'].astype(str)
        final_df = final_df.where(pd.notnull(final_df), None)

        transactions = final_df.to_dict("records")

        for row in transactions:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = None

        # for row in transactions:
        #     if any(pd.isna(v) for v in row.values()):
        #         # print(row)
        #         break

        anomalies = [r for r in transactions if r["is_anomaly"]]

        return {
            'summary': summary,
            'category_breakdown': final_df.groupby('category')['amount'].sum().to_dict(),
            'anomalies': anomalies,
            'transactions': transactions,
        }
    
    def load_csv(self, file):
        file.seek(0)
        return pd.read_csv(file)

    def data_cleaning(self, df):
        df['date'] = pd.to_datetime(df['date'], format='mixed').dt.date
        df['amount'] = (df['amount'].astype(str).str.replace(r'[^\d.]', '', regex=True).astype(float))
        df['currency'] = df['currency'].str.upper()
        df['status'] =  df['status'].str.upper()
        df['category'] = df['category'].fillna("Uncategorized")
        return df

    def anomaly_detection(self, df):
        median = df.groupby('account_id')['amount'].transform('median')
        df['is_anomaly'] = (df['amount'] > median*3)
        df['anomaly_reason'] = None
        df.loc[df["is_anomaly"], "anomaly_reason"] = "Amount exceeds 3x account median"
        
        domestic_brands = ["SWIGGY","OLA","IRCTC"]
        domestic_mask = ((df["currency"] == "USD")&(df["merchant"].str.upper().isin(domestic_brands)))
        df.loc[domestic_mask,"is_anomaly"] = True
        df.loc[domestic_mask,"anomaly_reason"] = "Domestic merchant with USD currency"

        return df

    def llm_classification(self, df):
        uncategorized = df[df['category']=='Uncategorized']
        if uncategorized.empty:
            return df
        
        transactions = uncategorized[['txn_id', 'merchant', 'amount', 'notes']].to_dict('records')

        prompt = f"""
        Classify each transaction into exactly one category:

        Food
        Shopping
        Travel
        Transport
        Utilities
        Cash Withdrawal
        Entertainment
        Other

        Return ONLY valid JSON.

        Example:

        [
            {{
                "txn_id": "TXN1000",
                "category": "Shopping"
            }}
        ]

        Transactions:
        {json.dumps(transactions, indent=2)}
        Return ONLY a JSON array.

        Do not use markdown.
        Do not use code fences.
        Do not add explanations.
        """

        try:
            content=self.call_llm_with_retry(prompt,'classification')
            result = json.loads(content)
        except Exception as e:
            # print("Failed to parse LLM response:")
            return df
        
        category_map = {
            item["txn_id"]: item["category"]
            for item in result
        }

        mask = ((df["category"] == "Uncategorized") & (df["txn_id"].isin(category_map.keys())))

        df.loc[mask, "category"] = (df.loc[mask, "txn_id"].map(category_map))

        return df
    
    def llm_summary(self, df):
        total_spend_by_currency = df.groupby('currency')['amount'].sum().to_dict()
        top_merchants = df.groupby('merchant')['amount'].sum().sort_values(ascending=False).head(3).to_dict()
        anomaly_count = int(df["is_anomaly"].sum())

        summary = {
            "total_spend_by_currency": total_spend_by_currency,
            "top_merchants": top_merchants,
            "anomaly_count": anomaly_count
        }

        prompt = f"""
        Given this transaction summary:

        {json.dumps(summary, indent=2)}

        Generate ONLY valid JSON:

        {{
            "spending_narrative": "2-3 sentence summary",
            "risk_level": "low"
        }}

        risk_level must be one of:
        low
        medium
        high

        Return only JSON.
        Do not use markdown.
        Do not use code fences.
        Do not add explanations.
        """

        try:
            content=self.call_llm_with_retry(prompt,"summary")
            llm_summary = json.loads(content)
        except Exception as e:
            # print("Failed to parse LLM summary", e)
            llm_summary = {"spending_narrative":"Summary Unavailable", "risk_level":"NA"}
        return {**summary, **llm_summary}

    def call_llm_with_retry(self, prompt, task):

        if settings.TESTING:
            if task == "classification":
                return """
                [
                    {
                        "txn_id": "TXN1000",
                        "category": "Shopping"
                    }
                ]
                """
            else:
                return """
                {
                    "spending_narrative": "Mock summary",
                    "risk_level": "low"
                }
                """

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0
                )

                return response.choices[0].message.content

            except Exception as e:
                print(f"LLM attempt {attempt + 1} failed: {e}")

                if attempt < 2:
                    time.sleep(2 ** attempt)  # 1s, 2s, 4s

        raise Exception("All retries failed")