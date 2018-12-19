
from collections import defaultdict, OrderedDict
from Framework import Analysis_Wrapper, Load_File, Settings

from .Write_Tables import Write_Tables

@Analysis_Wrapper()
def Print_Ware_Stats(file_name = 'ware_stats'):
    '''
    Gather up all ware statistics, and print them out.
    Produces csv and html output.
    Will include changes from enabled extensions.

    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "ware_stats".
    '''
    wares_file = Load_File('libraries/wares.xml')
    t_file = Load_File('t/0001-L044.xml')
    ware_dict_list = []

    # Loop over the ware nodes; only first level children.
    for ware in wares_file.Get_Root_Readonly().findall('./ware'):

        # Do the initial field parsing, putting them into a dict.
        fields_dict = Parse_Ware(ware)
        ware_dict_list.append(fields_dict)
        
        # Do text lookups.
        if 't_name' not in fields_dict:
            # Default to the id.
            fields_dict['name'] = fields_dict['id']
        else:
            # Let the t-file Read handle the lookup.
            fields_dict['name'] = t_file.Read(fields_dict['t_name'])
            
        if 't_factory' not in fields_dict:
            # Blank factory.
            fields_dict['factory'] = ''
        else:
            # Let the t-file Read handle the lookup.
            fields_dict['factory'] = t_file.Read(fields_dict['t_factory'])

            
    # Sort the wares.
    ware_dict_list = sorted(ware_dict_list, 
                            key = lambda x : (x['group'], x['transport'], x['name']))


    # Filter out unused attributes.
    used_attributes = []
    for ware_dict in ware_dict_list:
        for key in ware_dict:
            if key not in used_attributes:
                used_attributes.append(key)
    # Order the attributes.
    attribute_order = []
    for attribute in attribute_names_ordered_dict:
        if attribute in used_attributes:
            attribute_order.append(attribute)


    # Form into a table.
    table = []

    # Make a header line.
    header = []
    for attribute in attribute_order:
        header.append(attribute_names_ordered_dict[attribute])
    table.append(header)

    for ware_dict in ware_dict_list:
        row = []
        for attribute in attribute_order:
            value = ware_dict.get(attribute)
            if value == None:
                value = ''
            row.append(value)
        table.append(row)

    # Write results.
    Write_Tables(file_name, table)
    return


def Parse_Ware(ware_node):
    '''
    Returns a dict with fields parsed out of the ware_node.
    '''
    fields_dict = OrderedDict()
    
    # Start with the easy fields.
    for key, xpath, xml_attr in ware_fields_table:
        node = ware_node.find(xpath)
        # Skip if node not found.
        if node == None:
            continue
        value = node.get(xml_attr)
        # Replace missing values with blanks.
        if value == None:
            value = ''
        fields_dict[key] = value

    # Fill in production nodes (can be multiple).
    # TODO: maybe use an intermediate structure for this to help compute
    # profit margin on production once top level wares filled in.
    for prod_index, prod_node in enumerate(ware_node.findall('./production')):
        prod_dict = OrderedDict()
        prod_dict['time']   = prod_node.get('time')
        prod_dict['amount'] = prod_node.get('amount')
        prod_dict['method'] = prod_node.get('method')
        prod_dict['name']   = prod_node.get('name')

        # Loop over wares.
        for ware_index, prod_ware_node in enumerate(prod_node.findall('./primary/ware')):
            prod_ware_dict = OrderedDict()
            prod_ware_dict['id']     = prod_ware_node.get('ware')
            prod_ware_dict['amount'] = prod_ware_node.get('amount')
            # Add a suffix and join into prod_dict.
            for key, value in prod_ware_dict.items():
                prod_dict['ware_{}_{}'.format(ware_index, key)] = value

        # TODO: maybe "effects" nodes.
        # Add a suffix and join into fields_dict.
        for key, value in prod_dict.items():
            fields_dict['prod_{}_{}'.format(prod_index, key)] = value


    # TODO: fill in computed stats (production profit, trade profit, 
    #  profit/volume, etc.).

    # % difference from min to max price.
    # Lots of terms on this, but basically just divide and round off.
    price_min = float(fields_dict.get('price_min','0'))
    price_max = float(fields_dict.get('price_max','0'))
    if price_min == 0:
        fields_dict['price_spread'] = ''
    else:
        fields_dict['price_spread'] = str(int(round(
            (price_max / price_min - 1) * 100)))

    return fields_dict


# Simple field lookups.
# Production nodes are more complicated.
ware_fields_table = [
    ('id'                 , '.'                , 'id'),
    ('t_name'             , '.'                , 'name'),
    ('t_factory'          , '.'                , 'factoryname'),
    ('group'              , '.'                , 'group'),
    ('transport'          , '.'                , 'transport'),
    ('volume'             , '.'                , 'volume'),
    ('tags'               , '.'                , 'tags'),
    
    ('price_min'          , '.price'           , 'min'),
    ('price_avg'          , '.price'           , 'average'),
    ('price_max'          , '.price'           , 'max'),
    ]


attribute_names_ordered_dict = OrderedDict((
    #('t_name'         , 'name'),
    #('t_factory'      , 'factoryname'),
    ('name'           , 'Name'),
    ('group'          , 'Group'),
    ('transport'      , 'Container'),
    ('volume'         , 'Volume'),

    ('price_min'      , 'Min'),
    ('price_avg'      , 'Average'),
    ('price_max'      , 'Max'),
    ('price_spread'   , 'Spread %'),
    
    ('factory'        , 'Factory'),

    # Manually fill out production/wares for the moment.
    #('prod_name_0'    , 'P0 Name'),
    ('prod_0_method'         , 'P0 Method'),
    ('prod_0_time'           , 'P0 Time'),
    ('prod_0_amount'         , 'P0 Amount'),
    ('prod_0_ware_0_id'      , 'P0 Ware'),
    ('prod_0_ware_0_amount'  , 'P0 Amount'),
    ('prod_0_ware_1_id'      , 'P0 Ware'),
    ('prod_0_ware_1_amount'  , 'P0 Amount'),
    ('prod_0_ware_2_id'      , 'P0 Ware'),
    ('prod_0_ware_2_amount'  , 'P0 Amount'),
    
    ('prod_1_method'         , 'P1 Method'),
    ('prod_1_time'           , 'P1 Time'),
    ('prod_1_amount'         , 'P1 Amount'),
    ('prod_1_ware_0_id'      , 'P1 Ware'),
    ('prod_1_ware_0_amount'  , 'P1 Amount'),
    ('prod_1_ware_1_id'      , 'P1 Ware'),
    ('prod_1_ware_1_amount'  , 'P1 Amount'),
    ('prod_1_ware_2_id'      , 'P1 Ware'),
    ('prod_1_ware_2_amount'  , 'P1 Amount'),
    
    ('prod_2_method'         , 'P2 Method'),
    ('prod_2_time'           , 'P2 Time'),
    ('prod_2_amount'         , 'P2 Amount'),
    ('prod_2_ware_0_id'      , 'P2 Ware'),
    ('prod_2_ware_0_amount'  , 'P2 Amount'),
    ('prod_2_ware_1_id'      , 'P2 Ware'),
    ('prod_2_ware_1_amount'  , 'P2 Amount'),
    ('prod_2_ware_2_id'      , 'P2 Ware'),
    ('prod_2_ware_2_amount'  , 'P2 Amount'),


    ('id'             , 'ID'),
    ('tags'           , 'Tags'),
    

))