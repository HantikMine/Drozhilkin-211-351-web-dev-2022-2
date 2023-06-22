from flask_login import current_user

class UsersPolicy:
    def __init__(self, record):
        self.record = record

    def create(self):
        return current_user.is_administrator()

    
    def delete(self):
        return current_user.is_administrator()

    def edit(self):
        if current_user.is_moderator():
            return True
        
        if str(current_user.id) == str(self.record.id):
            return True
            
        return False