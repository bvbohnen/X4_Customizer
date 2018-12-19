'''
Transforms to jobs.
'''
from fnmatch import fnmatch
from Framework import Transform_Wrapper, Load_File
from .Support import *

@Transform_Wrapper()
def Adjust_Job_Count(
        # Allow job multipliers to be given as a loose list of args.
        *job_multipliers
    ):
    '''
    Adjusts job ship counts using a multiplier, affecting all quota fields.
    Input is a list of matching rules, determining which jobs get adjusted.

    Resulting non-integer job counts are rounded, with a minimum of 1 unless
    the multiplier or original count were 0.

    * job_multipliers:
      - Tuples holding the matching rules and job count multipliers,
        ("key  value", multiplier).
      - The "key" specifies the job field to look up, which will
        be checked for a match with "value".
      - If a job matches multiple rules, the first match is used.
      - Supported keys:
        - 'id'      : Name of the job entry; supports wildcards.
        - 'faction' : The name of the faction.
        - 'tags'    : One or more tags, space separated.
        - 'size'    : The ship size suffix, 's','m','l', or 'xl'.
        - '*'       : Matches all jobs; takes no value term.

    Examples:
    <code>
        Adjust_Job_Count(1.2)
        Adjust_Job_Count(
            ('id       masstraffic*'      , 0.5),
            ('tags     military destroyer', 2  ),
            ('tags     miner'             , 1.5),
            ('size     s'                 , 1.5),
            ('faction  argon'             , 1.2),
            ('*'                          , 1.1) )
    </code>
    '''
    assert isinstance(job_multipliers, (list, tuple))
    #-Removed, don't worry about this for now.
    ## If the call happened to be unnamed but packed in a list, it may
    ##  now be double-wrapped, so unwrap once.
    #if len(job_multipliers) == 1 and isinstance(job_multipliers[0], list):
    #    job_multipliers = job_multipliers[0]
    
    # Put matching rules in standard form.
    rules = Standardize_Match_Rules(job_multipliers)
    
    jobs_game_file = Load_File('libraries/jobs.xml')
    xml_root = jobs_game_file.Get_Root()
        
    # Loop over the jobs.
    for job in xml_root.findall('./job'):
        
        # Look up the tags and a couple other properties of interest.
        job_id      = job.get('id')
        # The category node may not be present.
        category = job.find('category')
        if category != None:
            faction  = category.get('faction')
            size     = category.get('size')
            # Parse the tags to separate them, removing
            #  brackets and commas splitting.
            tags     = [x.strip(' []') for x in category.get('tags').split(',') if x]
        else:
            faction  = None
            size     = None
            tags     = []

        # Check the matching rules.
        multiplier = None
        for key, value, mult in rules:
            if((key == '*')
            or (key == 'id' and fnmatch(job_id, value))
            or (key == 'faction' and faction == value)
            # Check all tags, space separated.
            or (key == 'tags' and all(x in tags for x in value.split(' ')))
            # For sizes, add a 'ship_' prefix to the match_str.
            or (key == 'size' and size == ('ship_'+value)) ):
                multiplier = mult
                break
        # Skip if no match.
        if multiplier == None:
            continue

        # Apply the multiplier to all fields of the quota node.
        # The only quota that might be skipped is 'variation', but
        #  go ahead and adjust it too for now.
        quota = job.find('quota')
        for name, value in quota.items():
            XML_Multiply_Int_Attribute(quota, name, multiplier)
                        
    jobs_game_file.Update_Root(xml_root)
    return
