import pandas as pd
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import re

# Local imports

import gemini

# config

using_phi = False

'''
    Utilities
'''
def extract_assistant(text):
    '''
        Gets only the assistant's response .
    '''
    pass

def extract_json(text):
    """
    Extract JSON data from a text string
    """
    # Find JSON pattern using regex
    # Look for content between triple backticks and json keyword
    pattern = r"```json\s*([\s\S]*?)\s*```"
    pattern_2 = r"\{\s*([\s\S]*?)\s\*\}"
    
    match = re.search(pattern, text)
    match_2 = re.search(pattern_2, text)

    if match:
        json_text = match.group(1)
        try:
            # Parse the extracted text as JSON
            json_data = json.loads(json_text)
            return json_data
        except json.JSONDecodeError as e:
            return f"Error parsing JSON: {e}"
    elif match_2:
        json_text = match_2.group(0)
        try:
            # Parse the extracted text as JSON
            json_data = json.loads(json_text)
            return json_data
        except json.JSONDecodeError as e:
            return f"Error parsing JSON: {e}"
    else:
        try:
            # Try to parse the entire text as JSON
            json_data = json.loads(text)
            return json_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            # If no JSON found, return a message
        finally:
            return "No JSON found in the text"

def initialize_llm():
    """
        Initialize the LLM (Only needed for Phi)
    """
    print("Initializing LLM...")
    if using_phi == True:
        model_name = "microsoft/phi-3-mini-4k-instruct"
        # Configure to run on GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        try:
            print(f"Loading {model_name} model...")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,  # Use FP16 to reduce VRAM usage
                device_map="auto"  # Optimize device usage
            )
            print("Model loaded successfully")
            return model, tokenizer, device
        except Exception as e:
            print(f"Error loading model: {e}")
            return None, None, None
    else:
        return "Gemini", None, None
'''
# Initialize LLM
model, tokenizer, device = initialize_llm()
if model is None:
    print("Failed to initialize LLM. Exiting.")
    return
'''

def query_creator(model, tokenizer, device, entity, context, user_prompt, query_num=2):
    """Use the LLM to create probable web search queries"""
    # Truncate inputs if they're too long
    max_content_length = 3900
    if len(context) > max_content_length:
        context = context[:max_content_length] + "..."
    
    if entity=="":
        middle_phrase = None
    else:
        middle_phrase = f"Create probable web search queries compatible with google search engine based on {entity} and {context}."
    # Create prompt for the model
    prompt = f"""
    <|user|>
    You are a web seach query creation expert.
    The user wants to find about: {user_prompt}.
    {middle_phrase}
    Give maximum of {query_num} queries.
    
    Format your response as valid JSON that can be parsed with json.loads(). 
    The JSON should have a "queries" key containing an array of web search queries.
    Only respond with the json. No additional information.
    <|assistant|>
    """
    
    # Generate response
    if using_phi == True:
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=250 if middle_phrase else 100,
                    temperature=0.35 if middle_phrase else .2,
                    do_sample=True,
                    repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id
                )
            
            generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            response = generated_text.strip()
            # Try to parse JSON from the response
            try:
                query_data = extract_json(response)
                return query_data.get('queries', [])
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from response: {e}")
                print(f"Response: {response}")
                return []
        except Exception as e:
            print(f"Error generating response: {e}")
            return []
    else:
        try:
            response = gemini.generate(prompt).strip().replace("```json", "").replace("```", "")
            return extract_json(response)
        except Exception as e:
            print(f"Failed to parse JSON from response: {e}")
            print(f"Response: {response}")
            return []
    
def next_page_decision(model, tokenizer, device, url, txt, user_prompt, query_num=2):
    """Use the LLM to create probable web search queries"""
    # Truncate inputs if they're too long

    # Temporarily removing - seems like the context variable is never defined in this function

    '''
    max_content_length = 3900
    if len(context) > max_content_length:
        context = context[:max_content_length] + "..."
    '''
    
    if url=="":
        middle_phrase = None
    else:
        middle_phrase = f"Is the webpage with URL {url} and {txt} related to the user's wants?"
    # Create prompt for the model
    prompt = f"""
    <|user|>
    You are a web seach expert.
    The user wants looks for: {user_prompt}.
    {middle_phrase}
    Give only a yes or no answer.
    
    Format your response as valid JSON that can be parsed with json.loads(). 
    The JSON should have a "answer" key containing an yes or no answer.
    Only respond with the json . No additional information.
    <|assistant|>
    """
    
    # Generate response
    if using_phi == True:
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=250 if middle_phrase else 100,
                    temperature=0.35 if middle_phrase else .2,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            response = generated_text.strip()
            # Try to parse JSON from the response
            try:
                query_data = extract_json(response)
                return query_data.get('answer', '')
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from response: {e}")
                print(f"Response: {response}")
                return []
        except Exception as e:
            print(f"Error generating response: {e}")
            return []
    else:
        try:
            response = gemini.generate(prompt).strip().replace("```json", "").replace("```", "")
            return extract_json(response).get('answer', '')
        except Exception as e:
            print(f"Failed to parse JSON from response: {e}")
            print(f"Response: {response}")
            return []

def infer_schema(fetched_pages, query, probable_schema, tokenizer, device, model):
    # Prepare content for schema generation
    page_samples = []
    total_chars = 0
    max_chars = 3000  # Limit to fit in context window
    
    for page in fetched_pages:
        # Add title and first part of content
        content = page.get("content", "")
        title = page.get("title", "Untitled")
        
        # Calculate how much content we can add
        sample_text = f"Title: {title}\n\nContent:\n{content[:100]}"
        
        if total_chars + len(sample_text) <= max_chars:
            page_samples.append(sample_text)
            total_chars += len(sample_text)
        else:
            break
    
    combined_content = "\n\n---\n\n".join(page_samples)
    middle_line = f"Adjust based on this probable schema {probable_schema}"
    # Create a schema generation prompt for your model
    prompt = f"""
    <|user|>
        You are an expert on creating dataset schemas for data analysis. 
        The core entity of the dataset is based on a user query {query}.
        The following is the content of {len(fetched_pages)} web pages based on this query .
        Your task is to construct a dataset schema that could represent this information effectively.
        {"Create a structured schema with appropriate data types that can be converted to tabular format." if len(probable_schema)==0 else ""}
        {middle_line if len(probable_schema)>0 else ""}
        
        Here's sample content from the pages:

        {combined_content}
        
        Format your response as valid JSON that can be parsed with json.loads().
        The JSON should provide the schema only . Include the name and the type of the fields .
    <|assistant|>
    """
    
    # Generate schema with the LLM
    if using_phi == True:
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=800,# limit the dataset field length
                    temperature=0.3,
                    do_sample=True,
                    repetition_penalty = 0.9,
                top_p = 75,
                pad_token_id=tokenizer.eos_token_id
                )
            
            generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            print(generated_text)
            # Try to extract JSON
            schema_json = extract_json(generated_text)
            return schema_json, generated_text
            
        except Exception as e:
            print(f"Error generating schema: {e}")
            return "Error", generated_text
    else:
        try:
            generated_text = gemini.generate(prompt).strip().replace("```json", "").replace("```", "")
            schema_json = extract_json(generated_text)
            return schema_json, generated_text
        except Exception as e:
            print(f"Failed to parse JSON from response: {e}")
            print(f"Response: {generated_text}")
            return "Error", generated_text
            
def check_relevance(url, schema, tokenizer, device, model):
    # Prepare content for schema generation
    prompt = f"""
    <|user|>
    You are an expert on analyzing the relevance of text.
    I have a dataset schema {schema}.
    I want to know if these {url} are likely to be related to the schema provided.
    Select the probable urls that might lead to raw data related to this schema. 
    The urls should immediately lead to raw data that can be used to fill the schema. 
    
    Format your response as valid JSON that can be parsed with json.loads().
    The JSON should include the reasoning process under the name reasoning and the the probable urls in a list under the name probable_urls.
    <|assistant|>
    """
    
    # Generate schema with the LLM
    if using_phi == True:
        inputs = tokenizer(prompt[:3000], return_tensors="pt").to(device)
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=300,# limit the dataset field length
                    temperature=0.175,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            # Try to extract JSON
            if generated_text:
                gen_schema = extract_json(generated_text)
                if isinstance(gen_schema,dict):
                    return gen_schema
            else: 
                return None
        except Exception as e:
            print(f"Error generating schema: {e}")
            return "Error", generated_text
    else:
        try:
            generated_text = gemini.generate(prompt).strip().replace("```json", "").replace("```", "")
            if generated_text:
                gen_schema = extract_json(generated_text)
                if isinstance(gen_schema, dict):
                    return gen_schema
        except Exception as e:
            print(f"Failed to parse JSON from response: {e}")
            print(f"Response: {generated_text}")
            return "Error", generated_text


    
def row_creation(text, schema , tokenizer , device , model):
    # Prepare content for schema generation
    prompt = f"""
    <|user|>
    You are an expert on extracting relevant information from text .
    I have a dataset schema {schema} .
    I want to create a row based on this text : {text}
    
    Format your response as valid JSON that can be parsed with json.loads().
    The JSON should include the reasoning process under the name reasoning and the row in a list under the name row .
    If the text is not related to the schema, return an empty row.
    <|assistant|>
    """
    
    # Generate schema with the LLM
    if using_phi == True:
        inputs = tokenizer(prompt[:3000], return_tensors="pt").to(device)
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=500,# limit the dataset field length
                    temperature=0.2,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            # Try to extract JSON
            if generated_text:
                gen_row = extract_json(generated_text)
                if isinstance(gen_row, dict):
                    return gen_row
            else: 
                return None
        except Exception as e:
            print(f"Error generating schema: {e}")
            return "Error", generated_text
    else:
        try:
            generated_text = gemini.generate(prompt).strip().replace("```json", "").replace("```", "")
            if generated_text:
                gen_row = extract_json(generated_text)
                if isinstance(gen_row, dict):
                    return gen_row
        except Exception as e:
            print(f"Failed to parse JSON from response: {e}")
            print(f"Response: {generated_text}")
            return "Error", generated_text