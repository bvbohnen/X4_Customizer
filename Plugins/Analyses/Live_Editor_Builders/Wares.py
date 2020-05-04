'''
Build ware objects.
Due to the xml file size, this has some problems with long runtime.
Extra complexity added to multithread and to dynamically detect
some fields.
'''

from multiprocessing import Pool, cpu_count
import time

from Framework import File_System, Load_File, Print
from Framework.Live_Editor_Components import *
# Convenience macro renaming.
E = Edit_Item_Macro
D = Display_Item_Macro

from ...Transforms.Support import Float_to_String


@Live_Editor_Object_Builder('wares')
def _Build_Ware_Objects():
    '''
    Returns a list of Edit_Objects for all found wares.
    Meant for calling from the Live_Editor.
    '''
    #t_file = Load_File('t/0001-L044.xml')
    # Look up the ware file.
    wares_file = Load_File('libraries/wares.xml')
    xml_root = wares_file.Get_Root_Readonly()
    
    # Get the ware nodes; only first level children.
    ware_nodes = wares_file.Get_Root_Readonly().findall('./ware')
        
    start_time = time.time()

    # TODO: maybe condition this on if Settings.disable_threading is
    # set or not.
    if 1:
        '''
        Try out multiprocessing to speed this up.

        Observations, letting python split up ware nodes"
        - Time goes from ~20 to ~30 seconds with 1 worker.
        - Down to ~10 seconds with 6 workers; not much gain.

        To possibly reduce data copy overhead, split up the ware nodes
        manually into lists, and send a single full list to each worker.
        - Down to 7-8 seconds from doing this.
        - Still not great, but more than 2x speedup, so it's something.
        - Note: for different process counts, best was at system
          max threads, with higher counts not losing much time.
        - Can let the Pool handle the thread counting automatically,
          and it does get close, though that doesn't help with picking
          the work unit size.
        - Update: after making production nodes conditional, normal
          runs went 20 to ~4.5 seconds, and this went down to ~2.5.
        
        Later observations:
        - The node ids tagged onto xml element tails seem to be
          transferred okay through pickling, except the one on the
          root node that has to be pruned.

        - The file system appears to get completely replicated for
          every thread, such that the wares file gets node ids
          applied once globally and once per thread.
          The global node ids are higher than the threads since they
          are offset somewhat by any prior loaded xml, while the threads
          all start from 0.

        - This node id discrepency means the loaded elements mess up
          the live editor patch matching, where editing maja snails
          ends up changing marines.

        - How can the stupid python threading be prevented from making
          such a dumb complete system copy that doesn't even catch
          everything? Eg. it should at least be copying the original
          node ids, not starting from scratch.
          - It seems like it goes:
            - Item gets created with paths
            - Item runs value init
            - Value init calls Load_File, expecting it to be a quick
              dict lookup.
            - Multiprocessing barfs on itself and makes a new copy
              of the file system that does not have the wanted
              file loaded, and has to reload it from disk (with
              diff patching).

        - Workaround: change how object building works, such that
          items are linked directly to their source game file and
          do not have to do a file system load.
          Further, tweak the pickler to keep the tag on the top
          element copied.
          Result: things seem to work okay now.
        '''

        # Pick the process runs needed to do all the work.
        # Leave 1 thread free for system stuff.
        num_processes = max(1, cpu_count() -1)
        max_nodes_per_worker = len(ware_nodes) // num_processes +1
        slices = []
        start = 0
        while start < len(ware_nodes):
            # Compute the end point, limiting to the last node.
            end = start + max_nodes_per_worker
            if end > len(ware_nodes):
                end = len(ware_nodes)
            # Get the slice and store it.
            slices.append( ware_nodes[start : end] )
            # Update the start.
            start = end

        # Use a starmap for this, since it needs to pass both the
        # wares file and the ware node. Starmap will splat out
        # the iterables.
        inputs = [(slice, wares_file) for slice in slices]

        pool = Pool()#processes = num_processes)
        ware_edit_objects = sum(pool.starmap(
            _Create_Objects, 
            inputs,
            ), [])
        
    else:
        # Single thread style.
        ware_edit_objects = _Create_Objects(ware_nodes, wares_file)
            
    Print('Ware Edit_Objects creation took {:0.2f} seconds'.format(
        time.time() - start_time))

    return ware_edit_objects


def _Create_Objects(ware_nodes, wares_file):
    '''
    Returns a list of objects for the given ware nodes.
    '''
    ret_list = []
    for ware_node in ware_nodes:
        # Use the id attribute as the base name.
        name = ware_node.get('id')
        assert name != None
        ware_edit_object = Edit_Object(name)
        
        # Do an xpath partial replacement to fill in the path
        # to the node from the file base.
        xpath_prefix = './ware[@id="{}"]'.format(name)
                    
        # Find production nodes, get their macros (can be multiple).
        # Note: doing this conditionally instead of using pre-created
        # macros reduced run time from 20 to 4 seconds. Most nodes
        # do not have the full 3 production subnodes, nor 3 wares
        # per production.
        extra_macros = []
        for prod_index, prod_node in enumerate(ware_node.findall('./production')):
            # Offset indices by 1, for display names and for xpaths.
            extra_macros += Get_Production_Macros(xpath_prefix, prod_index +1)            
            # Loop over wares.
            for ware_index, prod_ware_node in enumerate(prod_node.findall('./primary/ware')):
                extra_macros += Get_Production_Ware_Macros(xpath_prefix, prod_index +1, ware_index +1)

        # Fill in the edit items from macros.
        ware_edit_object.Make_Items(
            wares_file, 
            ware_item_macros + extra_macros,
            xpath_replacements = {'PREFIX': xpath_prefix}
            )
        ret_list.append(ware_edit_object)
    return ret_list



# TODO: this gets called 4 times for the 4 versions, which
# seems overkill if the text file doesn't change.
# Maybe consider a special flag for items that are the same
# across versions, so they only do one lookup.
def Display_Update_Ware_Name(
        t_name_entry,
        id
    ):
    'Look up ware name.'
    # If no t_name_entry available, use the id name.
    if not t_name_entry:
        return id
    else:
        #t_file = File_System.Load_File('t/0001-L044.xml')
        # Let the t-file Read handle the lookup.
        #name = t_file.Read(t_name_entry)
        name = File_System.Read_Text(t_name_entry)
        return name
    

def Display_Update_Factory_Name(
        t_factory
    ):
    'Look up factory name.'
    if t_factory:
        #t_file = File_System.Load_File('t/0001-L044.xml')
        # Let the t-file Read handle the lookup.
        #return t_file.Read(t_factory)
        return File_System.Read_Text(t_factory)
    return


def Display_Update_Price_Spread(
        price_min,
        price_max,
    ):
    '''
    Calc % difference from min to max price.
    '''
    if price_min and price_max:
        price_min = float(price_min)
        price_max = float(price_max)
        if price_min != 0:
            return str(int(round((price_max / price_min - 1) * 100))) + '%'
    return
    

# Fields from the weapon macro file to look for and convert to Edit_Items.
# These xpaths will need partial replacements for the base node offset,
# since multiple wares are defined in the same file.
ware_item_macros = [
    D('name'                  , Display_Update_Ware_Name                    , 'Name', ''),
    E('t_name_entry'          , 'PREFIX'                 , 'name'           , 'T Name Entry', ''),
    E('id'                    , 'PREFIX'                 , 'id'             , 'ID', ''),
    E('group'                 , 'PREFIX'                 , 'group'          , 'Group', ''),
    E('transport'             , 'PREFIX'                 , 'transport'      , 'Transport', ''),
    E('price_min'             , 'PREFIX/price'           , 'min'            , 'Price Min', ''),
    E('price_avg'             , 'PREFIX/price'           , 'average'        , 'Price Avg', ''),
    E('price_max'             , 'PREFIX/price'           , 'max'            , 'Price Max', ''),
    D('price_spread'          , Display_Update_Price_Spread                 , 'Price Spread', ''),    
    E('volume'                , 'PREFIX'                 , 'volume'         , 'Volume', ''),
    E('tags'                  , 'PREFIX'                 , 'tags'           , 'Tags', ''),
    D('factory'               , Display_Update_Factory_Name                 , 'Factory', ''),
    E('t_factory'             , 'PREFIX'                 , 'factoryname'    , 'T Factory', ''),
    ]


def Get_Production_Macros(xpath_prefix, production_index):
    'Make production node macros. Indices should start at 1.'
    x = xpath_prefix
    p = production_index
    return [
    E('prod_{}_name'  .format(p), '{}/production[{}]'.format(x,p), 'name'  , 'Prod.{} T Name'  .format(p), ''),
    E('prod_{}_method'.format(p), '{}/production[{}]'.format(x,p), 'method', 'Prod.{} Method'.format(p), ''),
    E('prod_{}_time'  .format(p), '{}/production[{}]'.format(x,p), 'time'  , 'Prod.{} Time'  .format(p), ''),
    E('prod_{}_amount'.format(p), '{}/production[{}]'.format(x,p), 'amount', 'Prod.{} #'.format(p), ''),
    ]

def Get_Production_Ware_Macros(xpath_prefix, production_index, ware_index):
    'Make production ware node macros. Indices should start at 1.'
    x = xpath_prefix
    p = production_index
    w = ware_index
    return [
    E('prod_{}_ware_{}_id'    .format(p,w), '{}/production[{}]/primary/ware[{}]'.format(x,p,w), 'ware'  , 'Prod.{} Ware {} ID'    .format(p,w), ''),
    E('prod_{}_ware_{}_amount'.format(p,w), '{}/production[{}]/primary/ware[{}]'.format(x,p,w), 'amount', 'Prod.{} Ware {} #'.format(p,w), ''),
    ]