
RULE_FULL,RULE_PASSIVE,RULE_PHASE,RULE_FAULT,RULE_HINT = 0,1,2,3,4
rules = {    # [rule_any, rule_side, rule_phase, rule_fault, rule_hint_delay, rule_hint_reward]
            RULE_FULL:          [True, True, True, False, False, False],
            RULE_PASSIVE:       [False, False, False, True, True, True],
            RULE_PHASE:         [True, True, True, True, False, True],
            RULE_FAULT:         [True, True, True, True, True, True],
            RULE_HINT:          [True, True, True, False, True, True],
        }
