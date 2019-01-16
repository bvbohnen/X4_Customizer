'''
Transforms to director scripts.
'''
from fnmatch import fnmatch
from Framework import Transform_Wrapper, Load_File, File_System
from .Support import *


# TODO: expand this with per-mission selections, though they
# will need more work finding the right nodes to edit.
@Transform_Wrapper()
def Adjust_Mission_Rewards(
        # Allow multipliers to be given as a loose list of args.
        multiplier = 1,
        adjust_credits   = True,
        adjust_notoriety = True,
    ):
    '''
    Adjusts generic mission credit and notoriety rewards by a flat multiplier.

    * multiplier
      - Float, value to adjust rewards by.
    * adjust_credits
      - Bool, if True (default) changes the credit reward.
    * adjust_notoriety
      - Bool, if True (default) changes the notoriety reward.
    '''

    '''
    The generic missions make use of LIB_Reward_Balancing, giving
    it a couple mission aspects (difficulty, complexity level)
    to get the reward credits and notoriety.

    To globally adjust payouts, just edit that LIB script.

    For credits:
        There are a few places to make the edit, but want to do it
        before the value gets rounded to the nearest 10.

        Can either edit an expression in an existing node, eg. the
        faction adjustment, or can insert a new instruction.
        Easiest is probably just to edit the rounding operation directly,
        since that is likely to be stable across version changes.

    For notoriety:
        There is no convenient rounding node, so edit the scaling
        node. That is more likely to change in patches, so do it
        carefully.
    '''
    lib_reward_file = Load_File('md/LIB_Reward_Balancing.xml')
    xml_root = lib_reward_file.Get_Root()
        
    if adjust_credits:
        # Find the credit rounding instruction.
        credit_node = xml_root.findall(
            './/cue[@name="Reward_Money"]//set_value[@name="$Value"][@exact="(($Value)i / 10) * 10"]')
        # Ensure 1 match.
        assert len(credit_node) == 1
        credit_node = credit_node[0]

        # Edit the operation to include an extra multiply.
        mult_str = Float_to_String(multiplier)
        credit_node.set('exact', '(($Value * {})i / 10) * 10'.format(mult_str))


    if adjust_notoriety:
        # Find the notoriety scaling instruction.
        # Don't do a strict match on the operation; leave it flexible.
        notoriety_node = xml_root.findall(
            './/cue[@name="Reward_Notoriety"]//set_value[@name="$Value"]')
        # Ensure 1 match.
        assert len(notoriety_node) == 1
        notoriety_node = notoriety_node[0]

        # Edit the min and max attributes to include an extra multiply.
        for attrib in ['min','max']:
            op = notoriety_node.get(attrib)
            op = op.replace('$Value', '($Value * {})'.format(mult_str))
            notoriety_node.set(attrib, op)
            x = notoriety_node.attrib

    lib_reward_file.Update_Root(xml_root)
    return



@Transform_Wrapper()
def Adjust_Mission_Reward_Mod_Chance(
        new_chance = 2,
    ):
    '''
    Adjusts generic mission chance to reward a mod instead of credits.
    The vanilla chance is 2% for a mod, 98% for credits.

    * mod_chance
      - Int, the new percent chance of rewarding a mod.
      - Should be between 0 and 100.
    '''
    '''
    Many generic missions repeat this bit of code:

    <do_any>
        <do_if value="not $RewardCr" weight="98">
            ...
        </do_if>
        <do_if value="not $RewardObj" weight="2">
            ...
        </do_if>
    </do_any>

    Can hunt down the appropriate nodes to make the edit.
    '''
    # Validate the mod_chance range.
    mod_chance = int(new_chance)
    if mod_chance < 0:
        mod_chance = 0
    elif mod_chance > 100:
        mod_chance = 100
        
    # Want the various generic mission scripts.
    # These all are prefixed with GM_
    game_files = File_System.Load_Files('md/GM_*')
       
    for game_file in game_files:
        xml_root = game_file.Get_Root()

        # Find the parent reward  node.
        reward_nodes = xml_root.xpath('//do_if[@value="$GenerateReward"]')
        if len(reward_nodes) != 1:
            continue

        # Pick out the two nodes of interest.
        high_nodes = reward_nodes[0].xpath('do_any/do_if[@value="not $RewardCr"][@weight="98"]')
        low_nodes  = reward_nodes[0].xpath('do_any/do_if[@value="not $RewardObj"][@weight="2"]')

        # 1 of each should have been found.
        if len(high_nodes) != 1 or len(low_nodes) != 1:
            continue

        # Make the edits.
        high_nodes[0].set('weight', str(100-mod_chance))
        low_nodes[0] .set('weight', str(mod_chance))

        game_file.Update_Root(xml_root)
    return