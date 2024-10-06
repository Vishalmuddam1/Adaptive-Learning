import autogen
import panel as pn
import openai
import os
import time
import asyncio
from typing import List, Dict
import logging
from src import globals
#from src.Agents.agents import agents_dict
from src.FSMs.fsm_teach_me import TeachMeFSM
from src.Agents.group_chat_manager_agent import CustomGroupChatManager, CustomGroupChat
from src.UI.reactive_chat import ReactiveChat
from src.UI.avatar import avatar
from enum import Enum

#logging.basicConfig(filename='debug.log', level=logging.DEBUG, 
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logging.basicConfig(level=logging.INFO, 
                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


os.environ["AUTOGEN_USE_DOCKER"] = "False"


###############################################
# ChatGPT Model
###############################################

gpt4_config_list = [
    {
        'model': "gpt-4o",
    }
]

# These parameters attempt to produce precise reproducible results
temperature = 0
max_tokens = 1000
top_p = 0.5
frequency_penalty = 0.1
presence_penalty = 0.1
seed = 53


gpt4_config = {"config_list": gpt4_config_list, 
               "temperature": temperature,
               "max_tokens": max_tokens,
               "top_p": top_p,
               "frequency_penalty": frequency_penalty,
               "presence_penalty": presence_penalty,
               "seed": seed
}

llm = gpt4_config

#################################################
# Define Agents
#################################################
from src.Agents.base_agent import MyBaseAgent
from src.Agents.conversable_agent import MyConversableAgent
from src.Agents.student_agent import StudentAgent
from src.Agents.knowledge_tracer_agent import KnowledgeTracerAgent
from src.Agents.teacher_agent import TeacherAgent
from src.Agents.tutor_agent import TutorAgent
from src.Agents.problem_generator_agent import ProblemGeneratorAgent
from src.Agents.solution_verifier_agent import SolutionVerifierAgent
from src.Agents.programmer_agent import ProgrammerAgent
from src.Agents.code_runner_agent import CodeRunnerAgent
from src.Agents.learner_model_agent import LearnerModelAgent
from src.Agents.level_adapter_agent import LevelAdapterAgent
from src.Agents.motivator_agent import MotivatorAgent
from src.Agents.agents import AgentKeys


class CodeRunnerVerifierAgent(MyConversableAgent):  
    description = """
            CodeRunnerVerifierAgent is a proficient and efficient assistant specialized in making sure that code executed by CodeRunnerAgent completed successfully. 
            """            

    system_message = """
            You are CodeRunnerVerifierAgent, a proficient and efficient assistant specialized in making sure that code executed by CodeRunnerAgent completed successfully. 
            """            
    def __init__(self, **kwargs):
        super().__init__(
            name="CodeRunnerVerifierAgent",
            human_input_mode="NEVER",
            system_message=self.system_message,
            description=self.description,
            **kwargs
        )


student = StudentAgent(llm_config=llm)
knowledge_tracer = KnowledgeTracerAgent(llm_config=llm)
teacher = TeacherAgent(llm_config=llm)
tutor = TutorAgent(llm_config=llm)
problem_generator = ProblemGeneratorAgent(llm_config=llm)
solution_verifier = SolutionVerifierAgent(llm_config=llm)

programmer_system_message = """
        You are ProgrammerAgent, a Python programming expert. 
        Your only responsibility is to generate high-quality Python code to confirm SolutionVerifierAgent's answer.        
    """
programmer = ProgrammerAgent(llm_config=llm, 
                             system_message = programmer_system_message,
                             description = programmer_system_message)
code_runner = CodeRunnerAgent(llm_config=llm)
code_runner_verifier = CodeRunnerVerifierAgent(llm_config=llm)
learner_model = LearnerModelAgent(llm_config=llm)
level_adapter = LevelAdapterAgent(llm_config=llm)
motivator = MotivatorAgent(llm_config=llm)




agents_dict = {
    AgentKeys.STUDENT.value: student,
    AgentKeys.KNOWLEDGE_TRACER.value: knowledge_tracer,
    AgentKeys.TEACHER.value: teacher,
    AgentKeys.TUTOR.value: tutor,
    AgentKeys.PROBLEM_GENERATOR.value: problem_generator,
    AgentKeys.SOLUTION_VERIFIER.value: solution_verifier,
    AgentKeys.PROGRAMMER.value: programmer,
    AgentKeys.CODE_RUNNER.value: code_runner,
    AgentKeys.CODE_RUNNER_VERIFIER.value: code_runner_verifier,
    AgentKeys.LEARNER_MODEL.value: learner_model,
    AgentKeys.LEVEL_ADAPTER.value: level_adapter,
    AgentKeys.MOTIVATOR.value: motivator,
}


##############################################
# Main Adaptive Learning Application
############################################## 
globals.input_future = None
script_dir = os.path.dirname(os.path.abspath(__file__))
progress_file_path = os.path.join(script_dir, '../../progress.json')
   
fsm = TeachMeFSM(agents_dict)

groupchat = CustomGroupChat(agents=list(agents_dict.values()), 
                              messages=[],
                              max_round=globals.MAX_ROUNDS,
                              send_introductions=True,
                              speaker_selection_method=fsm.next_speaker_selector
                              )


manager = CustomGroupChatManager(groupchat=groupchat,
                                filename=progress_file_path, 
                                is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0 )    

# Allow the fsm to get the groupchat history
fsm.register_groupchat_manager(manager)


# Begin GUI components
reactive_chat = ReactiveChat(groupchat_manager=manager)


# Register groupchat_manager and reactive_chat gui interface with ConversableAgents
# Register autogen reply function
# TODO: Consider having each conversible agent register the reply function at init
for agent in groupchat.agents:
    agent.groupchat_manager = manager
    agent.reactive_chat = reactive_chat
    agent.register_reply([autogen.Agent, None], reply_func=agent.autogen_reply_func, config={"callback": None})



#Load chat history on startup
manager.get_chat_history_and_initialize_chat(filename=progress_file_path, chat_interface=reactive_chat.learn_tab_interface) 
reactive_chat.update_dashboard()    #Call after history loaded



# --- Panel Interface ---
def create_app():    
    return reactive_chat.draw_view()

if __name__ == "__main__":    
    app = create_app()
    #pn.serve(app, debug=True)
    pn.serve(app, callback_exception='verbose')
 