from logging import config
from uuid import uuid4

from db_models.database import DatabaseConfig
from storage.project import Project

from connectors.manager import connection_manager

from storage.persistence import persistence

from storage.conversation import Conversation

from datetime import datetime


class ProjectManager:

    def __init__(self):

        self.projects = {}

        self.current_project = None

        self.load_projects()

    ########################################################

    def create_project(self, title, db_config):

        connector = connection_manager.connect(title, db_config)


        project = Project(
            id=str(uuid4()),
            title=title,
            connection_name=title,
            database_config=db_config,
            connector=connector,
        )

        project.create_conversation("Chat 1")

        self.projects[project.id] = project

        self.current_project = project.id

        self.save_projects()

        return project

    ########################################################

    def get_project(self, project_id):

        return self.projects.get(project_id)

    ########################################################

    def get_current_project(self):

        if self.current_project is None:
            return None

        return self.projects[self.current_project]

    ########################################################
    def switch_project(self, project_id):

        if project_id not in self.projects:
            return

        self.current_project = project_id

        self.save_projects()
        
    ########################################################

    def delete_project(self, project_id):

        if project_id not in self.projects:
            return

        project = self.projects[project_id]

        connection_manager.disconnect(project.connection_name)

        del self.projects[project_id]

        if self.current_project == project_id:

            self.current_project = None
        
        self.save_projects()

    ########################################################

    def list_projects(self):

        return list(self.projects.values())

    ########################################################

    def rename_project(self, project_id, new_title):

        self.projects[project_id].title = new_title

        self.save_projects()

    def new_chat(self, project_id):

        project = self.projects[project_id]

        conversation = project.create_conversation()

        self.save_projects()

        return conversation
    
    def get_active_conversation(self):

        project = self.get_current_project()

        if project is None:

            return None

        return project.get_active_conversation()
    
    ########################################################

    def create_conversation(
        self,
        project_id,
        title="New Chat"
    ):

        project = self.projects[project_id]

        conversation = project.create_conversation(title)

        self.save_projects()

        return conversation

    ########################################################

    def switch_conversation(
        self,
        project_id,
        conversation_id
    ):

        project = self.projects[project_id]

        project.switch_conversation(
            conversation_id
        )

        self.save_projects()

    ########################################################

    def get_current_conversation(self):

        project = self.get_current_project()

        if project is None:

            return None

        return project.get_active_conversation()
    
    ########################################################

    def save_projects(self):

        persistence.save(self)


    def load_projects(self):

        data = persistence.load()

        if data is None:

            return

        self.current_project = data["current_project"]

        for p in data["projects"]:

            connector = connection_manager.connect(
                p["title"],
                DatabaseConfig(**p["database_config"])
            )

            project = Project(
                id=p["id"],
                title=p["title"],
                connection_name=p["connection_name"],
                database_config=DatabaseConfig(
                    **p["database_config"]
                ),
                connector=connector
            )

            project.active_conversation = p["active_conversation"]

            for conv in p["conversations"]:

                project.conversations.append(

                    Conversation(

                        id=conv["id"],

                        title=conv["title"],

                        thread_id=conv["thread_id"],

                        created_at=datetime.fromisoformat(
                            conv["created_at"]
                        )
                    )

                )

            self.projects[project.id] = project