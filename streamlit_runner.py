import streamlit as st
import pandas as pd
import os
import docx
import json

from langchain.chat_models import AzureChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage


if "compliance_data" not in st.session_state:
    st.session_state.compliance_data = None
    
if "contract_data" not in st.session_state:
    st.session_state.contract_data = None
    
if "task_data" not in st.session_state:
    st.session_state.task_data = None

if "verdict_task_data" not in st.session_state:
    st.session_state.verdict_task_data = None
    
model = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    openai_api_version=os.getenv("OPENAPI_VERSION"),
    azure_deployment=os.getenv("GPT_DEPLOYMENT_NAME"),
)

def getText(file):
    doc = docx.Document(file)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

def create_compliance_json(contract):
    prompt = '''
extract all key terms from the contract and structure them in a JSON format.

Terms may be related to different sections and subsections of the contract, which should be reflected in your JSON
Contract:
''' + contract
    system_message = SystemMessage(content=prompt)
    result = model([system_message])
    return result.content

def compliance_check_for_task(conditions, row):
    prompt = '''
Take the task and task's budget and check if it meets the the contract conditions. If a task description violates one or more conditions, you should specify the reason for the violation.
If it is possible to increase the budget using some reason, then it should be increased. 
''' + json.dumps(row, indent=0)[1:-1] + '''
Contract conditions:
''' + conditions + '''
The verdict:
'''
    system_message = SystemMessage(content=prompt)
    result = model([system_message]).content
    row['Verdict'] = result
    return row

uploaded_contract = st.file_uploader("Upload contract in docx format", type=["docx"])
if uploaded_contract is not None:
    contract = getText(uploaded_contract)
    st.session_state.contract_data = contract

    
uploaded_tasks = st.file_uploader("Upload tasks in xlsx format or csv with ; separator", type=["xlsx", "csv"])
if uploaded_tasks is not None:
    filename, file_extension = os.path.splitext(uploaded_tasks.name)
    try:
        if file_extension=='.xlsx':
            tasks = pd.read_excel(uploaded_tasks, engine='openpyxl')
        elif file_extension=='.csv':
            tasks = pd.read_csv(uploaded_tasks, sep=';')
        st.session_state.task_data = tasks
    except:
        st.error('Wrong format')
        

with st.sidebar:
    if st.session_state.contract_data:
        if st.button("Create conditions"):
            st.session_state.compliance_data = create_compliance_json(contract)
    if st.session_state.compliance_data and st.session_state.task_data is not None:
        if st.button("Analyze tasks"):
            new_res = []
            for val in list(st.session_state.task_data.T.to_dict().values()):
                new_res.append(compliance_check_for_task(st.session_state.compliance_data, val))
                df = pd.DataFrame(new_res)
            st.session_state.verdict_task_data = df

    if st.session_state.compliance_data:
        with st.sidebar:
            st.download_button(
                label="Download conditions file",
                file_name="conditions.json",
                mime="application/json",
                data=st.session_state.compliance_data,
            )
        
if st.session_state.verdict_task_data is not None:
    st.table(st.session_state.verdict_task_data)
    with st.sidebar:
        csv_data = st.session_state.verdict_task_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download verdicts full file",
            file_name="task_verdicts.csv",
            mime='text/csv',
            data=csv_data,
        )

    
    
