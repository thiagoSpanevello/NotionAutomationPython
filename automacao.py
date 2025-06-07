import os
import time
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

load_dotenv()

notion_token = os.getenv("NOTION_TOKEN")
database_id = os.getenv("NOTION_DATABASE_ID")
sigaa_username = os.getenv("SIGAA_USERNAME")
sigaa_password = os.getenv("SIGAA_PASSWORD")

headers = {
    "Authorization": f"Bearer {notion_token}",
    "Content-Type": "application/json",
    "Notion-Version": "2021-05-13"
}

def buscar_tarefas_no_notion():
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=headers, json={})
    if response.status_code == 200:
        data = response.json()
        return {t["properties"]["Nome"]["title"][0]["text"]["content"] for t in data.get("results", [])}
    else:
        print(f"Erro ao buscar tarefas: {response.status_code} - {response.text}")
        return set()

def adicionar_tarefa_no_notion(nome, status, descricao, data):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Nome": {"title": [{"text": {"content": nome}}]},
            "Status": {"multi_select": [{"name": status}]},
            "Descrição": {"rich_text": [{"text": {"content": descricao}}]},
            "Data": {"date": {"start": data}}
        }
    }
    print(f"Adicionando tarefa '{nome}' ao Notion...")
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Tarefa '{nome}' adicionada com sucesso!")
    else:
        print(f"Erro ao adicionar tarefa: {response.status_code} - {response.text}")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://sigaa.uffs.edu.br/sigaa/verTelaLogin.do")


driver.find_element(By.NAME, "user.login").send_keys(sigaa_username)
senha_field = driver.find_element(By.NAME, "user.senha")
senha_field.send_keys(sigaa_password)
senha_field.send_keys(Keys.RETURN)

time.sleep(5)
driver.get("https://sigaa.uffs.edu.br/sigaa/portais/discente/discente.jsf")
time.sleep(5)

avaliacao_portal = driver.find_element(By.ID, "avaliacao-portal")
table = avaliacao_portal.find_element(By.TAG_NAME, "table")
rows = table.find_elements(By.TAG_NAME, "tr")[1:]

tarefas_list = []
nome_materia_atual = None

for row in rows:
    tds = row.find_elements(By.TAG_NAME, "td")
    if len(tds) < 3:
        continue

    data_hora_text = tds[1].text.strip().split(" (")[0]
    try:
        data = datetime.strptime(data_hora_text, "%d/%m/%Y %H:%M")
        data_str = data.strftime("%Y-%m-%dT%H:%M:%S")
        data_br = data.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        print(f"Data inválida: {data_hora_text}")
        continue

    td_conteudo = tds[2]
    try:
        status = "Fazer"
        small_tag = td_conteudo.find_element(By.TAG_NAME, "small")
        nome_materia_atual = small_tag.text.strip().split("\n")[0]

        texto_completo = td_conteudo.text.strip()
        nome_tarefa = texto_completo.split("Tarefa:")[-1].strip() if "Tarefa:" in texto_completo else ""

        if nome_tarefa:
            tarefas_list.append((nome_materia_atual, nome_tarefa, data_str, data_br, status))
        else:
            print("Erro: Nome da tarefa vazio!")
    except Exception as e:
        print(f"Erro ao processar tarefa: {e}")

driver.quit()

tarefas_existentes = buscar_tarefas_no_notion()

for nome_materia, nome_tarefa, data_str, data_br, status in tarefas_list:
    if nome_tarefa not in tarefas_existentes:
        descricao = nome_materia
        adicionar_tarefa_no_notion(nome_tarefa, status, descricao, data_str)
    else:
        print(f"Tarefa '{nome_tarefa}' já está no Notion, ignorando...")
