from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware


# 1. Loaded env
load_dotenv()

# 2. Allowed origins for CORS
origin = ["http://localhost:5173"]


# 3. Create app function for defining fastapi app
def create_app():
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origin,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
