import json
import os

DATA_FILE = "storage/data/projects.json"


class Persistence:

    def save(self, project_manager):

        data = {
            "current_project": project_manager.current_project,
            "projects": []
        }

        for project in project_manager.projects.values():

            p = {
                "id": project.id,
                "title": project.title,
                "connection_name": project.connection_name,
                "database_config": project.database_config.model_dump(),
                "active_conversation": project.active_conversation,
                "conversations": []
            }

            for conv in project.conversations:

                p["conversations"].append({
                    "id": conv.id,
                    "title": conv.title,
                    "thread_id": conv.thread_id,
                    "created_at": str(conv.created_at)
                })

            data["projects"].append(p)

        os.makedirs("storage/data", exist_ok=True)

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    #######################################################

    def load(self):

        if not os.path.exists(DATA_FILE):

            return None

        with open(DATA_FILE) as f:

            return json.load(f)


persistence = Persistence()