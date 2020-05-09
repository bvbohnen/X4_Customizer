
__all__ = [
    'doc_matching_rules',
    ]

doc_matching_rules = '''
    Ship transforms will commonly use a group of matching rules
    to determine which ships get modified, and by how much.   

    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform
        defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will
        be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - Supported keys for ships:
        - 'name'    : Internal name of the ship macro; supports wildcards.
        - 'purpose' : The general role of the ship. List of purposes:
          - mine
          - trade
          - build
          - fight
        - 'type'    : The ship type. List of types:
          - courier, resupplier, transporter, freighter, miner,
            largeminer, builder
          - scout, interceptor, fighter, heavyfighter
          - gunboat, corvette, frigate, scavenger
          - destroyer, carrier, battleship
          - xsdrone, smalldrone, police, personalvehicle,
            escapepod, lasertower
        - 'class'   : The class of ship. List of classes:
          - 'ship_xs'
          - 'ship_s'
          - 'ship_m'
          - 'ship_l'
          - 'ship_xl'
          - 'spacesuit'
        - '*'       : Matches all ships; takes no value term.

    Examples:
    <code>
        Adjust_Ship_Speed(1.5)
        Adjust_Ship_Speed(
            ('name ship_xen_xl_carrier_01_a*', 1.2),
            ('class ship_s'                  , 2.0),
            ('type corvette'                 , 1.5),
            ('purpose fight'                 , 1.2),
            ('*'                             , 1.1) )
    </code>
    '''
