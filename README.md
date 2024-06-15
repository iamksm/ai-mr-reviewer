# iamksm Bot

The main objective of this bot is to streamline the review process. It offers a preliminary review to assist you in rectifying minor issues or oversights before your Merge Request (MR) is subjected to a final review by your colleague.

## Usage

### Pre-requisite

- [Setup ollama](https://ollama.com/download)
- [Setup NGINX](https://ubuntu.com/tutorials/install-and-configure-nginx#1-overview)
- [Setup Webhook on Gitlab](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html#create-a-webhook)
- A VM/Server (preferrably running linux)

### Steps

1. On a provisioned VM, create a python environment with python3.8+ and install this package.
2. Create a config file `config.yml` using the format in [`config-example.yml`](config-example.yml) with actual values and on linux set the environment variable `CONFIG_FILE_PATH` value to the path to the config file you created
3. Setup NGINX to route all incoming requests to the bot that we will be running at port 7777
4. Download your preferred model using `ollama pull <model name>` [Available models here](https://www.ollama.com/library)
4. Run the bot using `gunicorn -w 2 iamksm_bot.app.webhook:AIR -b 0.0.0.0:7777 -k gevent --threads 4`

Alternatively, you can build the image and run it locally with most of the above already setup.

1. from the project dir, run `docker build -t iamksm-bot:0.0.1 .`
2. Run docker compose up -d

#### Note: Make sure the model you plan to use is already downloaded

## Here’s how it works:

1. 🧰 **MR Type**
    - Identifies the category of this MR. It could be one of the following:
        - **💡 Feature**: Adds a new feature to the application.
        - **💩 Bugfix**: Fixes a known bug or issue in the application.
        - **🦺 Chore**: Involves project-related tasks that aren't directly associated with the application code.
        - **🧹 Housekeeping**: Includes general maintenance tasks to keep the codebase clean and well-organized.
        - **📡 Enhancement**: Enhances an existing feature or functionality.
        - **📝 Documentation**: Involves changes solely to the project's documentation.
        - **📌 Refactoring**: Involves modifying the code structure without changing its behavior.
        - **🧶 Style**: Involves changes that don't alter the meaning of the code (white-space, formatting, missing semi-colons, etc).
        - **🧪 Performance Improvement**: Involves changes that enhance the application's performance.

2. 👀 **Change Introduction**
    - Provides context using the MR title, description, and commit info.
    - Emphasizes the main objectives of the MR and its impact on the overall project.

3. 🧐 **Review**
    - Proposes improvements, updates, or revisions based on the changes.
    - Determines whether the MR fulfills its purpose based on its commit message(s) and the provided description.
    - Checks whether the code and tests handle edge cases.
    - Provides examples of the desired change.

4. 📚 **Code Quality and Best Practices**
    - Ensures compliance with the Google Style Guides for the programming language used.
    - Looks for code smells and anti-patterns.
    - If applicable, proposes better design patterns or coding practices.

5. 💬 **Comments and Suggestions**
    - Bases its feedback and suggestions on the changes made in the MR.
    - States it's decision on the MR (approved, needs work, rejected) with clear reasoning.

6. 🤔 **Decision**
    - The ultimate decision. Can be
        - ✅ Approved
        - 🚧 Needs Work
        - ❌ Rejected as necessary.

If the bot identifies any issues with your MR, it will initiate a thread. However, if your MR passes the bot’s review, it will simply leave a comment and approve the MR.
