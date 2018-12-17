
from lxml import etree as ET
from collections import defaultdict, OrderedDict
from Framework import Analysis_Wrapper, File_System, Settings

@Analysis_Wrapper()
def Print_Weapon_Stats():
    '''
    Gather up all weapon statistics, and print them out.
    Currently only supports csv output.
    Will include changes from enabled extensions.
    '''
    weapons_dict = Collect_Weapons()

    # Categorize by type (eg. 'turret').
    type_weapons_dict_dict = defaultdict(dict)
    for name, weapon in weapons_dict.items():
        type_weapons_dict_dict[weapon['weapon_class']][name] = weapon

    # Collect a list of tables (themselves lists of lists).
    table_list = []
    
    # Loop over the types.
    for weapon_type, weapons_dict in sorted(type_weapons_dict_dict.items()):

        # A list of lists will make up the table.
        # First entry is the weapon type.
        # Second entry is the column labels.
        table = []
        table_list.append(table)
        #table.append(['weapon_type:',weapon_type])

        # Determine which fields are in use.
        # Treat '0' as not in use, since in some cases an attribute
        # is always None or 0.
        attributes_used = set()
        for weapon in weapons_dict.values():
            for attr_name, value in weapon.items():
                if value not in [None, '0']:
                    attributes_used.add(attr_name)
        
        # -Removed; use the fixed order in attribute_print_order.
        ## Pick a display order for the attributes.
        ## Preorder a couple fields.
        #attributes_list = ['Name']
        ## Grab the rest of the attributes in sorted order.
        #for name in sorted(attributes_used):
        #    # Skip some attributes.
        #    if name in ['t_name_entry']:
        #        continue
        #    if name in attributes_list:
        #        continue
        #    attributes_list.append(name)

        # Join the ordered list with the used attributes.
        attributes_to_print = [attr for attr in attribute_names_ordered_dict
                                if attr in attributes_used]
            
        # Record column labels.
        table.append([attribute_names_ordered_dict[x] 
                      for x in attributes_to_print])

        # Sort the weapons by name and record them.
        for name, weapon in sorted(weapons_dict.items()):
            line = []
            table.append(line)
            for attr_name in attributes_to_print:
                # Just use blanks for unused entries.
                # Also, don't print 0's, to declutter the boolean columns.
                value = weapon.get(attr_name, None)
                if value in [None, '0']:
                    value = ''
                line.append(value)


    # Now pick a format to print to.
    # CSV initially.
    with open(Settings.Get_Output_Folder() / 'weapon_stats.csv', 'w') as file:
        for table in table_list:
            for line in table:
                file.write(', '.join(line) + '\n')
            # Put extra space between tables.
            file.write('\n')

    # HTML style.
    with open(Settings.Get_Output_Folder() / 'weapon_stats.html', 'w') as file:
        for table in table_list:
            xml_node = Table_To_Html(table)
            file.write(ET.tostring(xml_node, pretty_print = True, encoding='unicode'))
            # Put extra space between tables.
            file.write('\n')

    return


def Table_To_Html(table):
    '''
    Returns an xml root node holding html style nodes with the
    contents of the given table (list of lists, first line
    being the columns headers).
    '''
    # Pick the css styles; these will be ';' joined in a 'style' attribute.
    # Using http://www.stylinwithcss.com/resources_css_properties.php
    # to look up options.
    table_styles = {
        # Single line instead of double line borders.
        'border-collapse' : 'collapse',
        # Not too clear on this; was an attempt to stop word wrap.
        #'width'           : '100%', 
        # Stop wordwrap on the names and headers and such.
        'white-space'     : 'nowrap', 
        # Get values to be centered instead of left aligned.
        'text-align'      : 'center',
        # TODO: play with captioning.
        'caption-side'    : 'left',
        # Margin between tables.
        'margin-bottom'   : '20px',
        }
    cell_styles = {
        # Give some room around the text before hitting the cell borders.
        # TODO: not working; if placed on the table, puts a giant
        # margin around the whole table.
        #'margin'          : '10px',
        # Adjust this with padding. Don't set this very high; it is really
        # sensitive.
        'padding'         : '2px',
        }
    root = ET.Element('table', attrib = {
        'border':'1',
        #'cellpadding' : '0', 
        #'cellspacing' : '0',
        # CSS styles, separated by ;
        'style' : ';'.join('{}:{}'.format(k,v) 
                           for k,v in table_styles.items()),
        })
    for index, line in enumerate(table):
        row = ET.Element('tr', attrib = {
                # CSS styles, separated by ;
                'style' : ';'.join('{}:{}'.format(k,v) 
                                   for k,v in cell_styles.items()),
                })
        root.append(row)
        for entry in line:
            if index == 0:
                tag = 'th'
            else:
                tag = 'td'
            col = ET.Element(tag, attrib = {
                # CSS styles, separated by ;
                'style' : ';'.join('{}:{}'.format(k,v) 
                                   for k,v in cell_styles.items()),
                })
            col.text = entry
            row.append(col)
    return root


def Collect_Weapons():
    '''
    Returns a dict of Weapon objects, keyed by name.
    '''
    weapon_dict     = {}
    projectile_dict = {}
    
    # Set file search patterns to use.
    # Weapons/missiles are in one spot, bullets another.
    # All of the ones of interest are the macros.
    for pattern in [
        'assets/props/WeaponSystems/*macro.xml',
        'assets/fx/weaponFx/macros/*macro.xml',
        ]:
        for virtual_path in File_System.Gen_All_Virtual_Paths(pattern):

            # Load the xml file.
            xml_file = File_System.Load_File(virtual_path)
            # Grab the root node, possibly modified by prior transforms.
            root = xml_file.Get_Root_Readonly()

            # Look up what type of object it is.
            object_class = root.find('.//macro').get('class')
            name         = root.find('.//macro').get('name')

            # Parse it into a class object.
            if object_class in ['weapon','missilelauncher','turret',
                                'missileturret','bomblauncher']:
                weapon = Weapon(root)
                weapon_dict[name] = weapon
            elif object_class in ['bullet','missile','bomb',
                                  'mine','countermeasure']:
                projectile = Projectile(root)
                projectile_dict[name] = projectile
            else:
                # There are also 'effectobject' things; ignore for now.
                pass


    # Connect up the weapons with their projectiles.
    for weapon in weapon_dict.values():
        bullet = projectile_dict[weapon['bullet_codename']]

        # Collect the bullet attributes into the weapon.
        for attr_name, value in bullet.items():
            # Copy over; don't worry about overwrite for now.
            # TODO: look into overwrites where the value changes.
            weapon[attr_name] = value


    # Look up the names.
    t_file = File_System.Load_File('t/0001-L044.xml')
    for weapon in weapon_dict.values():
        # Start with no name.
        weapon['t_name'] = None
        if weapon['codename'] == 'weapon_tel_l_beam_01_mk1_macro':
            bla = 0

        # If a weapon has no Codename, skip it.
        if 't_name_entry' not in weapon:
            continue
        # Let the file Read handle the lookup.
        weapon['t_name'] = t_file.Read(weapon['t_name_entry'])

    return weapon_dict
    

def Parse_XML(object, xml_node, lookup_patterns):
    '''
    Parse some xml values into attributes for the object.

    * lookup_patterns
      - List of tuples of (object attribute, xpath, xml node attribute)
    '''
    for weapon_attr, xpath, xml_attr in lookup_patterns:
        node = xml_node.find(xpath)
        # Skip if node not found.
        if node == None:
            continue
        value = node.get(xml_attr)
        # Skip if values not found.
        if value == None:
            continue
        object[weapon_attr] = value
    return
    

class Weapon(dict):
    '''
    Base class for weapons; subclassed from dict.
    '''
    def __init__(self, xml_node):
        Parse_XML(self, xml_node, [
            ('codename'             , './/macro'                , 'name'),
            ('weapon_class'         , './/macro'                , 'class'),
            ('t_name_entry'         , './/identification'       , 'name'),
            ('rotation_speed'       , './/rotationspeed'        , 'max'),
            ('bullet_codename'      , './/bullet'               , 'class'),
            ('hull'                 , './/hull'                 , 'max'),
            
            # Typical for lasers.
            ('rotation_acceleration', './/rotationacceleration' , 'max'),
            ('heat_overheat'        , './/heat'                 , 'overheat'),
            ('heat_cool_delay'      , './/heat'                 , 'cooldelay'),
            ('heat_cool_rate'       , './/heat'                 , 'coolrate'),
            ('heat_reenable'        , './/heat'                 , 'reenable'),

            # For turrets.
            ('reload_rate'          , './/reload'               , 'rate'),
            ('reload_time'          , './/reload'               , 'time'),
            
            # For missile turrets.
            ('ammunition'           , './/ammunition'           , 'tags'),
            ('storage_capacity'     , './/storage'              , 'capacity'),
            ])
        # TODO: WeaponCon_01 from the parent file (non-macro_ version) to
        # get weapon size.
        

class Projectile(dict):
    '''
    Base class for bullets, missiles, bombs, etc.
    '''
    def __init__(self, xml_node):
        Parse_XML(self, xml_node, [
            # Typical for bullets.
            ('bullet_codename'           , './/macro'                , 'name'),
            ('ammunition_value'          , './/ammunition'           , 'value'),
            ('ammunition_reload'         , './/ammunition'           , 'reload'),
            ('bullet_speed'              , './/bullet'               , 'speed'),
            ('bullet_lifetime'           , './/bullet'               , 'lifetime'),
            ('bullet_amount'             , './/bullet'               , 'amount'),
            ('bullet_barrel_amount'      , './/bullet'               , 'barrelamount'),
            ('bullet_timediff'           , './/bullet'               , 'timediff'),
            ('bullet_angle'              , './/bullet'               , 'angle'),
            ('bullet_max_hits'           , './/bullet'               , 'maxhits'),
            ('bullet_ricochet'           , './/bullet'               , 'ricochet'),
            ('bullet_scale'              , './/bullet'               , 'scale'),
            ('bullet_attach'             , './/bullet'               , 'attach'),
            ('heat'                      , './/heat'                 , 'value'),
            ('reload_rate'               , './/reload'               , 'rate'),
            ('damage'                    , './/damage'               , 'value'),
            ('damage_shield'             , './/damage'               , 'shield'),
            ('damage_hull'               , './/damage'               , 'hull'),
            ('damage_repair'             , './/damage'               , 'repair'),
            
            # typical for missiles.          
            ('missile_amount'            , './/missile'              , 'amount'),
            ('missile_barrel amount'     , './/missile'              , 'barrelamount'),
            ('missile_lifetime'          , './/missile'              , 'lifetime'),
            ('missile_range'             , './/missile'              , 'range'),
            ('missile_guided'            , './/missile'              , 'guided'),
            ('missile_retarget'          , './/missile'              , 'retarget'),            
            ('damage'                    , './/explosiondamage'      , 'value'),
            ('damage_shield'             , './/explosiondamage'      , 'shield'),
            ('damage_hull'               , './/explosiondamage'      , 'hull'),
            ('reload_time'               , './/reload'               , 'time'),
            ('missile_hull'              , './/hull'                 , 'max'),
            ('lock_time'                 , './/lock'                 , 'time'),
            ('lock_range'                , './/lock'                 , 'range'),
            ('lock_angle'                , './/lock'                 , 'angle'),
            ('counter_resilience'        , './/countermeasure'       , 'resilience'),
            
            # No new fields for bombs.
            # Mines have some stuff for trigger and more range fields;
            # ignore for now.
            ])


attribute_names_ordered_dict = OrderedDict((
    ('t_name'                    , 'Name'),
    ('weapon_class'              , 'Class'),

    #('t_name_entry'              , ''),

    ('reload_time'               , 'Reload Time'),
    ('reload_rate'               , 'Reload Rate'),

    # Ammo values aren't very useful.
    # For missiles, ammo is either dumbfire or guided, but that
    # is captured in missile_guided.
    # Ammo value is always 1 for missiles, None or 999 for weapons.
    # Reload is always 0 or None, except for bomb launcher where it is 2.
    #('ammunition'                , ''),
    #('ammunition_value'          , ''),
    ('ammunition_reload'         , 'Ammo Reload'),
        
    ('damage'                    , 'Damage'),
    ('damage_shield'             , '+Shield'),
    ('damage_hull'               , '+Hull'),
    ('damage_repair'             , '+Repair'),
    
    ('bullet_speed'              , 'Speed'),
    ('bullet_lifetime'           , 'Lifetime'),
    ('bullet_amount'             , 'Amount'),
    ('bullet_barrel_amount'      , 'Barrel Amount'),
    ('bullet_timediff'           , 'Time Diff'),
    ('bullet_angle'              , 'Angle'),
    ('bullet_max_hits'           , 'Max Hits'),
    ('bullet_ricochet'           , 'Ricochet'),
    ('bullet_scale'              , 'Scale'),
    ('bullet_attach'             , 'Attach'),

    ('missile_amount'            , 'Amount'),
    ('missile_barrel amount'     , 'Barrel Amount'),
    ('missile_lifetime'          , 'Lifetime'),
    ('missile_range'             , 'Range'),
    ('missile_guided'            , 'Guided'),
    ('missile_retarget'          , 'Retarget'),
    
    ('missile_hull'              , 'Hull(missile)'),
    ('lock_time'                 , 'Lock Time'),
    ('lock_range'                , 'Lock Range'),
    ('lock_angle'                , 'Lock Angle'),
    ('counter_resilience'        , 'Resiliance'),
    
    ('heat'                      , '+Heat'),
    ('heat_overheat'             , 'Overheat'),
    ('heat_cool_delay'           , 'Cool Delay'),
    ('heat_cool_rate'            , 'Cool Rate'),
    ('heat_reenable'             , 'Reenable'),
    
    ('rotation_speed'            , 'Rot. Speed'),
    ('rotation_acceleration'     , 'Rot. Accel.'),
    ('storage_capacity'          , 'Storage'),
    
    ('hull'                      , 'Hull'),
    ('codename'                  , 'Weapon Codename'),
    ('bullet_codename'           , 'Bullet Codename'),
))