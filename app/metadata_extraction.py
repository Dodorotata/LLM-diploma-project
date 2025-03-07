# This script is to extract data from all patents (filename is assumed to be patentid.extention) in a specified folder using a defined local LLM model.
# LLM output is constrained using {Guidance} which is prompted from a Pydantic model.
# Output is validated against the Pydanic model and next stored in a SQLite database.
#-------------------------------------------------------------------------------------------------------------------------------------------------------------

import sqlite3
from llama_cpp import Llama
import os
from pathlib import Path
from pypdf import PdfReader
from datetime import datetime
import guidance
from guidance import models, gen, select
import json
from pydantic import BaseModel, Field
from typing import List
import argparse

DB_CONN = None
DB_FILE = None

def get_connection():
    global DB_CONN
    global DB_FILE
    if DB_CONN is None:
        DB_CONN = sqlite3.connect(DB_FILE)
    return DB_CONN

def get_cursor():
    cur = get_connection().cursor() # DB_CONN.cursor()
    return cur

def create_table():
    conn = get_connection()
    cur = get_cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS patent_metadata(
    patentid TEXT PRIMARY KEY,
    timestamp REAL,
    summary TEXT,
    key_technological_field TEXT,
    novelty_level TEXT,
    novelty_level_reason TEXT,
    medical_device_category TEXT,
    invasive TEXT,
    active TEXT,
    software TEXT,
    measuring_function TEXT,
    trained_professional_user TEXT);
    """)
    conn.commit()
    cur.close()

def initialize_llm(path):
    print(f"Loading LLM from path {path}")
    model = Llama(path, n_gpu_layers=10, n_ctx=0, echo=False, verbose=False)
    lm = guidance.models.LlamaCpp(model=model, echo=False, silent=False)
    print("Finished loading LLM")
    return lm

class PatentMetadata(BaseModel):
    summary: str = Field(..., description="generate summary of the invention in 1 sentence", min_length=10)
    key_technological_field: str = Field(..., description="list 5 key technological concepts in 1-3 words described in patent", min_length=10)
    novelty_level: str = Field(..., description="select one value from provided examples to define level of novelty of invention", examples=['LOW', 'MEDIUM', 'HIGH'])
    novelty_level_reason: str = Field(..., description="describe reason for chosen novelty_level in 1 sentece", min_length=10)
    medical_device_category: str = Field(...,
                                         description="choose device category from provided examples",
                                         examples=['Clinical chemistry and clinical toxicology devices',
                                                   'Hematology and pathology devices',
                                                   'Immunology and microbiology devices',
                                                   'Anesthesiology devices',
                                                   'Cardiovascular devices',
                                                   'Dental devices',
                                                   'Gastroenterology-urology devices',
                                                   'General and plastic surgery devices',
                                                   'General hospital and personal use devices',
                                                   'Neurological devices',
                                                   'Obstetrical and gynecological devices',
                                                   'Ophthalmic devices',
                                                   'Orthopedic devices',
                                                   'Physical medicine devices',
                                                   'Radiology devices'])
    invasive: str = Field(...,
                          description="Is the device'invasive', where 'invasive' means that any part of device penetrates inside the body?",
                          examples=['yes', 'no'])
    active: str = Field(...,
                        description="Is the device 'active' meaning device contains software or device operation depends on a source of energy other than that generated by the human body for that purpose, or by gravity, and which acts by changing the density of or converting that energy?",
                        examples=['yes', 'no'])
    software: str = Field(...,
                          description="Does the device contain software or is connected to a device with software?",
                          examples=['yes', 'no'])
    measuring_function: str = Field(...,
                                    description="Does the device have a 'measuring function' meaning it is intended to quantify parameters and the result of the measurement in displayed?",
                                    examples=['yes', 'no'])
    trained_professional_user: str = Field(...,
                               description="Does the device require trained professional medical personel to be used?",
                               examples=['yes', 'no'])

@guidance
def get_metadata(lm, text, pydantic_class):
    lm += f'''\
    Patent is delimited by (start) and (stop):
    (start)
    {text}
    (stop)

    JSON ouput: {{'''

    for key, value in pydantic_class.model_fields.items():
        if value.examples:
            lm += '"' + value.description + " " + ', '.join(value.examples) + '": "' + select(options=value.examples, name=key) + '",'
        elif value.annotation == str:
            lm += '"' + value.description + '": "' + gen(name=key, stop='"') + '",'
        elif value.annotation == int:
            lm += '"' + value.description + '": "' + gen(name=key, regex="[0-9]+") + '",'
    lm += '}'
    return lm

def outupt_to_dict(pydantic_class, output):
    metadata_dict = {}
    for key in pydantic_class.model_fields.keys():
        metadata_dict[key] = output[key]
    return metadata_dict

def output_dict_to_pydantic(pydantic_class, metadata_dict):
    '''Transorms output from lm/guidance -> dict -> original pydantic model'''
    output_pydantic_model = pydantic_class(**metadata_dict)
    return output_pydantic_model

def insert_record(cur, patentid, output_pydantic):
    timestamp = datetime.timestamp(datetime.now())
    output_vals = (patentid, timestamp, *output_pydantic.model_dump().values())
    cur.execute("""INSERT INTO patent_metadata VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(patentid) DO UPDATE SET
                summary=excluded.summary,
                timestamp=excluded.timestamp,
                key_technological_field=excluded.key_technological_field,
                novelty_level=excluded.novelty_level,
                novelty_level_reason=excluded.novelty_level_reason,
                medical_device_category=excluded.medical_device_category,
                invasive=excluded.invasive,
                active=excluded.active,
                software=excluded.software,
                measuring_function=excluded.measuring_function,
                trained_professional_user=excluded.trained_professional_user
            WHERE excluded.timestamp>patent_metadata.timestamp;""", output_vals)
    get_connection().commit()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, required=True, help="/home/dorota/LLM-diploma-project/app/patents")
    parser.add_argument("--db_file", type=str, required=True, help="/home/dorota/LLM-diploma-project/db/patent_metadata.db")
    parser.add_argument("--model_file", type=str, required=True, help="/home/dorota/models/mistral-7b-instruct-v0.2.Q6_K.gguf or /home/dorota/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf")
    parser.add_argument("--reprocess", action='store_true', help="True flag if existing patents should be reprocessed")
    return parser.parse_args()


if __name__ == "__main__":
    
    args = parse_args()
    data_dir = args.data_dir
    DB_FILE = args.db_file
    model_file = args.model_file
    reprocess = args.reprocess

    if not Path(data_dir).is_dir():
        print(f"Provided data directory {data_dir} does not exist or is not readable")
        exit(1)
    
    if not Path(model_file).is_file():
        print(f"Provided model file {model_file} does not exist or is not readable")
        exit(1)

    create_table()

    lm = initialize_llm(model_file)

    for filename in os.listdir(data_dir):
        cur = get_cursor()
        patentid = filename.split('.')[0]
        print(f'extracting metadata from {patentid}')

        if reprocess:
            exists = False
        else:
            cur.execute(f"SELECT 1 FROM patent_metadata WHERE patentid = ?", (patentid,))
            exists = cur.fetchone()

        if exists:
            print(f'{patentid} already exists')
            continue
        else:
            try:
                file = os.path.join(data_dir, filename)
                reader = PdfReader(file) 
                num_pages = len(reader.pages)
                TEXT = ""
                for page_num in range(num_pages):
                    page = reader.pages[page_num]  
                    TEXT += page.extract_text()
            except Exception as e:
                print(f"Exception in file {file}. Skipping.")
                print(e)
                continue 
            
            output = lm + get_metadata(TEXT, PatentMetadata)
            output_dict = outupt_to_dict(PatentMetadata, output)

            try:
                output_pydantic = output_dict_to_pydantic(PatentMetadata, output_dict)
            except Exception as e:
                print(f"Got exceptioin {e} trying to crate Pydantic model. Skipping file {file}")
                print(output_dict)
                continue
            
            insert_record(cur, patentid, output_pydantic)
            print(f'done extracting from {patentid}')

        cur.close()

    get_connection().close()


    