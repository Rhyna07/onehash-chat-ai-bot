from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from os.path import join, dirname, abspath
from dotenv import load_dotenv
import boto3
from cache import is_chatbot_cached, cache_chatbot_data, get_chatbot_data, delete_chatbot_data
from util import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt, extract_text_from_url
import openai
from openai import OpenAI  # Import the OpenAI library

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")  # Add your OpenAI API key to .env

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

app = FastAPI()

origins = [
    "*",  # Add the URL of your frontend server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add the origin URL of your frontend server
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],  # Allow all headers for testing purposes
)

# Initialize OpenAI API client
openai.api_key = OPEN_AI_API_KEY

@app.get('/')
async def read_root():
    return {"message": "Python microservice is alive"}

@app.post('/chatbot')
async def create_chatbot(
    bot_files: List[UploadFile] = File(None),
    bot_urls: List[str] = Form([]),
    bot_text: str = Form(''),
    # below 2 parameters must be passed to API
    chatbot_id: str = Form(...),
    temperature: float = Form(0.7)
):
    try:
        temperature = float(temperature)
        # Define the directory and filename for the temporary file
        temp_file_path = join(abspath(dirname(__file__)), f"{chatbot_id}.txt")

        # Extract text from uploaded files
        if bot_text != '':
            bot_text += '\n'
        if bot_files:
            for bot_file in bot_files:
                if bot_file.filename.endswith('.pdf'):
                    pdf_text = extract_text_from_pdf(bot_file)
                    bot_text += pdf_text + '\n'
                elif bot_file.filename.endswith('.docx'):
                    docx_text = extract_text_from_docx(bot_file)
                    bot_text += docx_text + '\n'
                elif bot_file.filename.endswith('.txt'):
                    txt_text = extract_text_from_txt(bot_file)
                    bot_text += txt_text + '\n'

        # Extract text from URLs
        if bot_urls:
            for url in bot_urls:
                url_text = extract_text_from_url(url)
                bot_text += url_text + '\n'

        # Write the extracted text to the temporary file
        with open(temp_file_path, 'w') as temp_file:
            temp_file.write(bot_text)

        # Upload the temporary file to S3
        s3.upload_file(
            Filename=temp_file_path,
            Bucket=S3_BUCKET_NAME,
            Key=f"{chatbot_id}.txt"
        )

        # Optionally, you can remove the temporary file after uploading
        os.remove(temp_file_path)

        return {"message": "Chatbot created successfully"}
    except Exception as e:
        error_message = str(e)
        # only for testing the application
        print("An error occurred:", error_message)
        raise HTTPException(status_code=500, detail=error_message)

@app.post('/prompt')
async def chat_with_chatbot(
    # below 2 parameters must be passed to API
    chatbot_id: str = Form(...),
    temperature: float = Form(0.7),
    user_message: str = Form(...)
):
    try:
        # Check if chatbot data is already cached
        if not is_chatbot_cached(chatbot_id):
            # Define the file path where you want to store the downloaded file
            downloaded_file_path = join(abspath(dirname(__file__)), f"{chatbot_id}.txt")

            # Download the file from S3
            s3.download_file(S3_BUCKET_NAME, f"{chatbot_id}.txt", downloaded_file_path)

            # Cache chatbot data
            with open(downloaded_file_path, 'r') as file:
                chatbot_data = file.read()
                cache_chatbot_data(chatbot_id, chatbot_data)

            # Delete the file from the local system
            os.remove(downloaded_file_path)

        # Generate prompt using the cached data
        prompt_text = get_chatbot_data(chatbot_id) + user_message
       
        
        client = OpenAI(
            api_key=os.environ.get("OPEN_AI_API_KEY"),
        )

        # Call OpenAI API to generate response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",  # Choose the model based on your preference
            messages=[{"role": "system", "content": prompt_text}],  # Include prompt as a system message
            temperature=temperature,
            max_tokens=150  # Adjust based on your requirements
        )
        
        # Extract response from chat completion
        response_text = response.choices[0].message.content.strip()
        
        return {"message": response_text}

    except Exception as e:
        error_message = str(e)
        # For testing purposes
        print("An error occurred:", error_message)
        raise HTTPException(status_code=500, detail=error_message)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3001)
