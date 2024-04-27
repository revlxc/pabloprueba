from dotenv import load_dotenv
load_dotenv()

import boto3
import os
import requests
import secrets
import gradio as gr
from openai import AzureOpenAI
from PyPDF2 import PdfReader
import fitz



def load_text_from_bucket(bucket_name):
    s3 = boto3.client('s3')
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        texts = []
        for page in pages:
            for obj in page.get('Contents', []):
                obj_key = obj['Key']
                if obj_key.lower().endswith('.pdf'):
                    try:
                        data = s3.get_object(Bucket=bucket_name, Key=obj_key)
                        file_content = data['Body'].read()
                        # Extract text from PDF
                        doc = fitz.open(stream=file_content, filetype="pdf")
                        text = ""
                        for page in doc:
                            text += page.get_text()
                        texts.append((obj_key, text))
                    except NoCredentialsError:
                        print("Credentials not available")
        return texts
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return []

def answer_question(question):
    # Consulta a Lakera para verificar si hay inyección de prompt
    lakera_response = requests.post(
        "https://api.lakera.ai/v1/prompt_injection",
        json={"input": question
              },
        headers={"Authorization": f"Bearer {os.getenv('LAKERA_API_KEY')}"},
    )

    lakera_response_json = lakera_response.json()
    pi_score = lakera_response_json["results"][0]["category_scores"]["prompt_injection"]
    pi_decision = lakera_response_json["results"][0]["categories"]["prompt_injection"]

    # Si Lakera Guard detecta una inyección de prompt, devuelve un mensaje apropiado
    if pi_decision:
        print(f"Prompt injection detected. Confidence: {pi_score:.3f}")
        print(lakera_response_json),
        return "Juanito dice que la consulta es malvada."

    # Consulta a Lakera para verificar si hay contenido sexual o odioso
    lakera_mod_response = requests.post(
        "https://api.lakera.ai/v1/moderation",
        json={"input": question},
        headers={"Authorization": f"Bearer {os.getenv('LAKERA_API_KEY')}"},
    )
    lakera_mod_response_json = lakera_mod_response.json()
    contains_hate = lakera_mod_response_json["results"][0]["categories"]["hate"]
    contains_sexual_content = lakera_mod_response_json["results"][0]["categories"][
        "sexual"
    ]
    hate_score = lakera_mod_response_json["results"][0]["category_scores"]["hate"]
    sexual_score = lakera_mod_response_json["results"][0]["category_scores"]["sexual"]

    if "results" in lakera_mod_response_json and (
        contains_hate or contains_sexual_content
    ):
        print("Hate or sexual content detected. Moderation required.")
        if contains_hate:
            print(f"Hate content detected. Confidence: {hate_score:.3f}")
        if contains_sexual_content:
            print(f"Sexual content detected. Confidence: {sexual_score:.3f}")

        return "Juanito dice que tiene contenido cochinon."

    bucket_name = os.getenv('BUCKETPRUEBALABPOC')
    pdf_texts = load_text_from_bucket(bucket_name)
    full_question = question
    for file_name, pdf_text in pdf_texts:
        full_question += " " + pdf_text

    message_text = [
        {"role": "system", "content": "You are an AI Security System that helps security engineers professionally."},
        {"role": "user", "content": question}
    ]

    response = client.chat.completions.create(
      model="JuanitoUseast2",  # modelo = "nombre_de_la_implementación"
      messages=message_text,
      temperature=0.7,
      max_tokens=800,
      top_p=0.95,
      frequency_penalty=0,
      presence_penalty=0,
      stop=None
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    # Authenticate with Azure OpenAI
    os.environ["AZURE_ENDPOINT"] = "https://juanitouseast2.openai.azure.com/"
    AZURE_API_KEY = os.getenv("AZURE_API_KEY")

    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_ENDPOINT"],
        api_key=AZURE_API_KEY,
        api_version="2024-02-15-preview"
    )

    # Create the Gradio interface
    iface = gr.Interface(fn=answer_question, inputs='text', outputs='text')
    iface.launch()