#!/usr/bin/env python3
'''
Created on 2010-10-03

Main module for running translator

@author: Marek Rogalski <mafikpl@gmail.com>
'''

from utils import Navigator
    
def build(node, rules):
    '''Executes rule handlers from module rules in postorder order.
    '''
    nav = Navigator(node)
    name = nav.rule_name()
    if not nav.rule_terminal():
        nav.children = [build(_, rules) for _ in node.value]
        if name in vars(rules):
            return vars(rules)[name](nav)
        else:
            return rules.empty(nav)
    else:
        return rules.terminal(nav)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Translate lojban text.", epilog="Input should be written on the standard input. Result of translation will be written on the standard output. Errors and warnings, will be displayed on the error stream.\n\nNote that polish translation requires poliqarp running locally.")
    parser.add_argument('-l', '--lang', dest='lang', help="destination language", required=True, choices=['pl'])
    #parser.add_argument('-p', '--poliqarp-port', dest='port', help="concordancer port (default is 4567)", default=4567, type=int)
    #parser.add_argument('-a', '--poliqarp-addr', dest='addr', help="concordancer address (default is localhost)", default='localhost')
    
    args = parser.parse_args()

    if args.lang == 'pl':
        import socket, sys, poliqarp.errors
        try:
            import pol.rules as rules
        except socket.error:
            print("Connection to poliqarpd on locashost:4567 refused.", file=sys.stderr)
            sys.exit(1)
        except poliqarp.errors.InvalidSessionId:
            print("Poliqarp session is invalid. Try removing /tmp/translator.pid", file=sys.stderr)
            sys.exit(1)

    try:
        import zirsam.dendrography
        toplevels = zirsam.dendrography.Stream()
        for node in toplevels:
            r = build(node, rules)
            print(r.translate())
    except KeyboardInterrupt:
        pass
