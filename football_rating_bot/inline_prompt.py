from enum import Enum

class InlineAction(Enum):
    UNKNOWN = 0,
    NEW_EVENT = 1,
    LIST_EVENT = 2,

class InlinePrompt:
    data_keys = [
        'action',
        'name',
        'max_count',
    ]

    descriptions = {
        'action' : '! for new event\n@ for list of events'
    }
    
    prompts = {
        'action': 'Input action:', 
        'dummy': 'Unknown error',               
        'max_count': 'Input max participants (max 55) [# - end symbols]',
        'name': 'Input name [# - end symbol]',
        'ready': 'Click here',
        'no_data': 'Input all required data'
    }

    MAX_PLAYERS = 55

    def __init__(self, text: str):
        self.input = { key: '' for key in InlinePrompt.data_keys}
        self.parse(text)

    def answer(self) -> str:
        if not self.check_data():
            return InlinePrompt.prompts['no_data']
        return self.input['name']
    
    def check_data(self) -> bool:
        return self.input['action'] and self.input['name'] and self.input['max_count']
    
    def description(self) -> str:
        try:
            return InlinePrompt.descriptions[self._prompt_key()]
        except KeyError:
            return ''

    def parse(self, text: str):
        if not text:
            return
        self.input['action'] = text[0]
        parts = text[1:].split('#')[:-1]
        self.input.update(dict(zip(InlinePrompt.data_keys[1:], parts)))
        self._convert_action()
        self._convert_max()

    def prompt(self) -> str:
        return InlinePrompt.prompts[self._prompt_key()]
    
    def _convert_action(self):
        action = InlineAction.UNKNOWN
        if self.input['action'] == '!':
            action = InlineAction.NEW_EVENT
        elif self.input['action'] == '@':
            action = InlineAction.LIST_EVENT
        self.input['action'] = action
    
    def _convert_max(self):
        try:
            max_count = int(self.input['max_count'])
            if max_count > InlinePrompt.MAX_PLAYERS:
                raise ValueError('Too many players')
            self.input['max_count'] = max_count
        except ValueError:
            self.input['max_count'] = 0

    def _prompt_key(self) -> str:
        if not self.input['action']:
            return 'action'
        if not self.input['name']:
            return 'name'
        if not self.input['max_count']:
            return 'max_count'
        return 'ready'
        
        
        


