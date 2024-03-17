import os
from configparser import ConfigParser

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain.vectorstores import FAISS
from sqlalchemy.orm import Session
from sqlalchemy import select
import model


class MethodologyCpability:
    def __init__(self) -> None: 
        # load config
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini")
        cf = ConfigParser()
        cf.read(file_path, encoding='utf-8')
        self.openai_api_key = cf.get('openai', 'api_key')
        self.openai_api_base = cf.get('openai', 'api_base')

        self.faiss_index_path = "./methodology/database/faiss_index"
        self.database_path = "./methodology/database/methodology.db"
        self.doc_path = "./methodology/doc"
        self.topk = 1

        self.relational_db = model.engine

        embeddings = OpenAIEmbeddings(openai_api_base=self.openai_api_base, openai_api_key=self.openai_api_key)

        if os.path.exists(self.faiss_index_path):
            print(f"Methodology faiss_index already exist, load index: {self.faiss_index_path}")
            self.vector_db = FAISS.load_local(self.faiss_index_path, embeddings)
        else:
            print(f"Methodology faiss_index {self.faiss_index_path} not exist, initializing new database...")

            empty_data = model.MethedologyInfo(
                id="0",
                scenario_description = "This is an empty methodology...",
                process_steps="",
                decision_points="",
                rules="",
                exception_handling="",
                suggestions="",
                reference_materails=""
            )

            docs = [Document(page_content=empty_data.__repr__())]

            self.vector_db = FAISS.from_documents(docs, embeddings)

            with Session(self.relational_db) as session:
                session.query(model.MethedologyInfo).delete()
                for k, _ in self.vector_db.docstore._dict.items():
                    empty_data.id = k
                    session.add(empty_data)
                session.commit()
        

    def search_methodology(self, task_description: str) -> list[str]:
        docs = self.vector_db.similarity_search(task_description, k = self.topk)
        
        methodoloy_list = []
        for doc in docs:
            methodoloy_list.append(doc.page_content)
        
        return methodoloy_list
       
    def add_methodology(self, texts:list[str]) -> list[str]:
        ids = self.vector_db.add_texts(texts=texts)
        self.vector_db.save_local(self.faiss_index_path)
        return ids

    def delete_methodology(self, ids:list[str]) -> bool | None:
        result = self.vector_db.delete(ids=ids)
        self.vector_db.save_local(self.faiss_index_path)
        return result

    """ 
    database operation 
    """ 
    def insert(self, new_metodology:model.MethedologyInfo) -> bool:
        id = self.add_methodology([new_metodology.__repr__()])[0]

        with Session(self.relational_db) as session:
            new_metodology.id = id
            session.add(new_metodology)
            session.commit()

        print(f"[Add] id = {id}")
        return True

    def delete(self, id:str) -> bool:
        result = self.delete_methodology([id])
        if False == result:
            print(f"[Del] Failed, id = {id}")
            return False
            
        with Session(self.relational_db) as session:
            session.query(model.MethedologyInfo).filter(model.MethedologyInfo.id == id).delete()
            session.commit()
        
        print(f"[Del] id = {id}")
        return True

    def list_all(self) -> list[list[str]]:
        methodology_list = []
        with Session(self.relational_db) as session:
            stmt = select(model.MethedologyInfo)

            methodology_list = [info.to_list_of_str() for info in session.scalars(stmt)]

        return methodology_list
                

    def list_id(self) -> list[str]:
        id_list = []
        with Session(self.relational_db) as session:
            stmt = select(model.MethedologyInfo.id)

            id_list = [id for id in session.scalars(stmt)]

        return id_list