'''
Transforms to jobs.
'''
from ..Common import Transform_Wrapper
from ..File_Manager import Load_File


@Transform_Wrapper()
def Adjust_Job_Count(
        # Allow job factors to be given as a loose list of args.
        *job_factors
    ):
    '''
    Adjusts job ship counts using a multiplier, affecting all quota fields.
    Caller provided matching rules determine which jobs get adjusted.
    Resulting non-integer job counts are rounded, with a minimum of 1 unless
    the multiplier or original count were 0.

    * job_factors:
      - Tuples holding the matching rules and job count  multipliers,
        (match_key, match_value, multiplier).
      - The match_key is one of a select few fields from the job nodes,
        against which the match_value will be compared.
      - Multiplier is an int or float, how much to adjust the job count by.
      - If a job matches multiple entries, the first match is used.
      - Supported keys:
        - 'faction': The name of the category/faction.
        - 'tag'    : A possible value in the category/tags list.
        - 'id'     : Name of the job entry, partial matches supported.
        - '*'      : Wildcard, always matches, takes no match_value.
        - 'masstraffic' : Mass traffic ship, takes no match_value.

    Example:
    Adjust_Job_Count(
        ('id','masstraffic', 0.5),
        ('tag','military', 2),
        ('tag','miner', 1.5),
        ('faction','argon', 1.2),
        ('*', 1.1) )
    '''
    assert isinstance(job_factors, (list, tuple))
    #-Removed, don't worry about this for now.
    ## If the call happened to be unnamed but packed in a list, it may
    ##  now be double-wrapped, so unwrap once.
    #if len(job_factors) == 1 and isinstance(job_factors[0], list):
    #    job_factors = job_factors[0]

    # Quick test of something.
    bla = Load_File('libraries/parameters.xml')

    jobs_game_file = Load_File('libraries/jobs.xml')
    xml_root = jobs_game_file.Get_Root()
    


    # Loop over the jobs.
    for job in xml_root.findall('./job'):
        # For convenience, break out the category node.
        # (May not be present.)
        category = job.find('category')

        # For this job, loop over match rules.
        # The first match will break out, leaving its factor set.
        # If no match found, default to 1x.
        factor = 1
        for entry in job_factors:
            # Check for wildcard, which has 2 terms.
            if entry[0] == '*':
                factor = entry[1]
                break
            # Otherwise expect 3 terms.
            key, value, factor = entry


            # Category node attributes.
            if category != None:
                if key == 'faction' and category.get(key) == value:
                    break
                # Tags have their value as a list string; for now, just look
                #  for the value being present in the string.
                # TODO: watch out for a tag name being encompassed by another
                #  tag name.
                if key == 'tag' and value in category.get('tags'):
                    break

            # Support partial id match.
            if key == 'id' and value in job.get(key):
                break

            # TODO: others.


        # Early skip if not changing counts.
        if factor == 1:
            continue


        # Apply the factor to all fields of the quota node.
        # The only quota that might be skipped is 'variation', but
        #  go ahead and adjust it too for now.
        quota = job.find('quota')
        for name, value in quota.items():
            # Multiply and round.
            new_value = int(round(int(value) * factor))
            # If neither original term was 0, set a min of 1.
            if value != 0 and factor != 0 and new_value == 0:
                new_value = 1
            quota.set(name, str(new_value))
            
    jobs_game_file.Update_Root(xml_root)
    return
