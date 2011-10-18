'''
Created on 2010-10-03

@author: Marek Rogalski <mafikpl@gmail.com>
'''
   
import zirsam.dendrography 

class Navigator: # TODO: elegantszy nawigator opakowujący więcej niż jedno drzewo
    '''Utility class for convenient browsing parse-tree and passing on the data.
    '''
    def __init__(self, rule):
        self.rule = rule
        self.object = None
        self.children = []
        
    def rule_terminal(self):
        '''True if a rule is a terminal in the grammar.
        '''
        return not isinstance(self.rule, zirsam.dendrography.MatchTracker)

    def rule_name(self):
        '''Returns short rule name.
        '''
        if isinstance(self.rule, zirsam.dendrography.MatchTracker):
            return str(self.rule.rule) 
        elif self.rule.type is Ellipsis:
            return type(self.rule).__name__
        else:
            return self.rule.type.__name__
        
    def text(self):
        return self.rule.text()
        
    def __str__(self):
        try:
            return "<Navigator: {} \"{}\">".format(self.rule_name(), self.text())
        except:
            return "<Navigator: {}>".format(self.rule_name())
    __repr__ = __str__
    
    def descendants_all(self, category):
        for child in self.children:
            if child.rule_name() == category:
                yield child
            for descendant in child.descendants_all(category):
                yield descendant
    
    def descendants_once(self, category):
        for child in self.children:
            if child.rule_name() == category:
                yield child
            else:
                for descendant in child.descendants_once(category):
                    yield descendant
    
    def __getattr__(self, rule):
        return [c for c in self.children if c.rule_name() == rule]
    
    def __dir__(self):
        return [c.rule_name() for c in self.children]
    
    def __contains__(self, rule):
        for c in self.children:
          if c.rule_name() == rule:
              return True
        return False

    def __getitem__(self, n):
        return self.children[n]
        
    def translate(self):
        if self.object:
            return self.object.translate()
        else:
            raise Exception('No object in toplevel navigator {}!'.format(self))
