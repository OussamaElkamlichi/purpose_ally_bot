from db_agent import goals_seeding, cron_seed

class UserGoals:
    def __init__(self, user_id):
        self.goals = {}
        self.extragoals = {}

    def add_main_goal(self, user_id, main_goal):
        if main_goal not in self.goals:
            self.goals[main_goal] = []
    
    def add_extra_maingoals(self, user_id, extra_main_goal):
        if extra_main_goal not in self.extragoals:
            self.extragoals[extra_main_goal] = []

    def add_sub_goal(self, user_id, main_goal, sub_goal):
        if main_goal in self.goals:
            self.goals[main_goal].append(sub_goal)

    def add_extra_subgoals(self, user_id, extra_main_goal, extra_sub_goal):
        if extra_main_goal in self.extragoals:
            self.extragoals[extra_main_goal].append(extra_sub_goal)

    def get_goals_list(self):
        if not self.goals:
            return "لا توجد أهداف."
        return "\n".join([f"{main_goal}: {', '.join(sub_goals)}" for main_goal, sub_goals in self.goals.items()])
        
    def get_extra_goals_list(self):
        if not self.extragoals:
            return "لا توجد أهداف."
        return "\n".join([f"{extra_main_goal}: {', '.join(extra_sub_goals)}" for extra_main_goal, extra_sub_goals in self.extragoals.items()])
        
    def launch(self, user_id):
        res = goals_seeding(self.goals, user_id)
        return res
    
    def extra_launch(self, user_id):
        res = goals_seeding(self.extragoals, user_id)
        return res
    
    def goals_count(self):
        return self.goals
    
    def extra_goals_count(self):
        return self.extragoals
    
    def cron_seed(self, user_id, params):
        res = cron_seed(user_id, params)
        return res
