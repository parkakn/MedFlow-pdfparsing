import glob
import os

from pdfminer.high_level import extract_text
from marker.convert import convert_single_pdf
from marker.models import load_all_models
from openai import OpenAI

# All PDF files to parse (assumed to be in content folder) 
content = glob.glob("content/*.pdf")  

## Pipeline: 
    # 1. extract text using pdfminer 
        # Pros: pdfminer extracts all texts very accurately.
        # Cons: no markdown file structure (specifiying headings, sections, etc.), no images extracted, extracted embedded tables are unstructured  

    # 2. use marker parse pdf file 
        # Pros: extracts images, tables, and text with markdown file structure
        # Cons: text extraction is not as accurate as pdfminer

    # 3. use LLM to update markdown file with text (fill missing texts, restructure)

## Dependencies: 
# Load models to use pdf converter
model_lst = load_all_models() 

# LLM system and user prompts:  
system_prompt = '''You are a Markdown editor that updates the makrdown file with provided text. 
The text file contains the correct text paragraphs. Using the text paragraphs in text, update the markdown file with any missing content or misordered sections. 
'''

def sys_prompt(text,markdown_content):
    prompt = f"""You are a Markdown editor and formatter. The text content contains the correct text paragraphs, but be aware of nosiy letters or characters. The Markdown file contains the correct format, but may have missing text content or misordered structure. 
Based on the correct text paragraphs, update the Markdown file with any missing content or misordered sections. Make sure to include all the text content in the Markdown file! 

------------------------------------
Text Content:
{text}

------------------------------------
Mardown Content:
{markdown_content}

------------------------------------
Give back the Markdown content with the corrections made.

Updated Markdown Content:     
    """
    return prompt

# Initialize OpenAI chat client 
client = OpenAI()

def chat(prompt):
    completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": prompt
        }
    ]
)
    return completion.choices[0].message

def clean_msg(msg):
    msg = msg.content.split("markdown\n")[1].split("```")[0]
    return msg

# Execute pipeline
for i in content:
    
    # 0. Get pdf file 
    fpath = i
    base_name = os.path.splitext(os.path.basename(fpath))[0]

    # 1. Extract text using pdfminer
    text = extract_text(fpath)

    # 2. parse PDF with marker
    markdown_content, images, out_meta = convert_single_pdf(fpath, model_lst)

    # 3. Use LLM to update markdown file with text
    print("LLM is updating markdown file with text...")
    prompt = sys_prompt(text,markdown_content)
    msg = chat(prompt)
    clean = clean_msg(msg)

    # 4. Save outputs 
    
    # Save text  
    output_dir = 'parsed_/text'
    os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist
    output_file_txt = os.path.join(output_dir, f'{base_name}.txt')
    output_file_md = os.path.join(output_dir, f'{base_name}.md')

    with open(output_file_txt, 'w') as txt_file:
        txt_file.write(clean)

    with open(output_file_md, 'w') as md_file:
        md_file.write(clean)

    print(f"Text saved to {output_file_txt} and {output_file_md}")

    # Save images
    output_dir = 'parsed_/images'
    os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist
    output_subdir = os.path.join(output_dir, base_name)
    os.makedirs(output_subdir, exist_ok=True)  # Ensure the subdirectory exists
    for filename, image in images.items():
        image.save(os.path.join(output_subdir, filename))

    print(f"Images saved to {output_subdir}")


