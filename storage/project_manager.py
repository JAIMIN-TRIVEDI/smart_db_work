from logging import config
from uuid import uuid4

from storage.project import Project

from connectors.manager import connection_manager


class ProjectManager:

    def __init__(self):

        self.projects = {}

        self.current_project = None

    ########################################################

    def create_project(self, title, db_config):

        connector = connection_manager.connect(title, db_config)

        project = Project(
            id=str(uuid4()),
            title=title,
            connection_name=title,
            database_config=db_config,
            connector=connector 
        )

        self.projects[project.id] = project

        self.current_project = project.id

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

    ########################################################

    def delete_project(self, project_id):

        if project_id not in self.projects:
            return

        project = self.projects[project_id]

        connection_manager.disconnect(project.connection_name)

        del self.projects[project_id]

        if self.current_project == project_id:

            self.current_project = None

    ########################################################

    def list_projects(self):

        return list(self.projects.values())

    ########################################################

    def rename_project(self, project_id, new_title):

        self.projects[project_id].title = new_title
