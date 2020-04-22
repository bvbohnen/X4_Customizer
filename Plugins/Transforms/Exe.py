'''
Transforms to the raw exe binary.
'''

from Framework import Transform_Wrapper, Load_File, File_System, Settings
from .Support import Binary_Patch
from .Support import Int_To_Hex_String
from .Support import Apply_Binary_Patch
from .Support import Apply_Binary_Patch_Group

NOP = '90'

@Transform_Wrapper()
def Remove_Sig_Errors():
    '''
    Suppresses file sigature errors from printing to the debug log, along
    with file-not-found errors.
    Written for Windows v3.10 exe.
    '''

    '''
    Note: function offset names taken from ghidra for the x4 steam
    windows exe version 3.10.
        
    FUN_140f15100 has the file not found error message.            
    FUN_140f14db0 has the sig failure message.

    There are different tricky ways of trying to suppress errors, but
    simplest is just to replace the Print call with nops.
    
    FUN_140f14db0:

        `                     LAB_140f14f25                     XREF[1]: 141fae2d8(*)  
        ` 140f14f25 49 83      CMP     qword ptr [R9 + 0x18],0x10
        `           79 18 10
        ` 140f14f2a 72 03      JC      LAB_140f14f2f
        ` 140f14f2c 4d 8b 09   MOV     R9,qword ptr [R9]
        `                   LAB_140f14f2f                     XREF[2]: 140f14f2a(j), 
        `                                                              141fae2e0(*)  
        ` 140f14f2f 89 44      MOV     dword ptr [RSP + local_88],EAX
        `           24 20
        Need to wildcard this offset (007c7d56 is added to addr togo down to the string).
        ` 140f14f33 4c 8d      LEA     R8,[s_File_I/O:_Failed_to_verify  = "File I/O: Failed to
        `           05 56 
        `           7d 7c 00
        ` 140f14f3a ba 01      MOV     EDX,0x1
        `           00 00 00
        ` 140f14f3f 33 c9      XOR     ECX,ECX
        Wildcard the call target.
        ` 140f14f41 e8 3a      CALL    FUN_140f0c280                     undefined FUN_140f0c28
        `           73 ff ff
     
    FUN_140f15100: 

        ` 140f15166 48 83      CMP     qword ptr [RBX + 0x48],0x10
        `           7b 48 10
        ` 140f1516b 48 8d      LEA     RDX,[RBX + 0x30]
        `           53 30
        ` 140f1516f 72 03      JC      LAB_140f15174
        ` 140f15171 48 8b 12   MOV     RDX,qword ptr [RDX]
        `                   LAB_140f15174                     XREF[1]: 140f1516f(j)  
        Wildcard this
        ` 140f15174 48 8d      LEA     RCX,[s_File_I/O:_Could_not_find_  = "File I/O: Could not
        `           0d 5d 
        `           7b 7c 00
        Wildcard this
        ` 140f1517b e8 b0      CALL    FUN_140f0c230                     undefined FUN_140f0c23
        `           70 ff ff
        ` 140f15180 bf 04      MOV     EDI,0x4
        `           00 00 00
        ` 140f15185 e9 89      JMP     LAB_140f15213
        `           00 00 00

    '''

    
    patches = [ 
        
    Binary_Patch(
        file = Settings.X4_exe_name,
        # Call is at the end of this block, since after the call is code
        # ghidra didn't understand, and so may be hard to pick out addresses.
        ref_code = '''
            49 83   
            79 18 10
            72 03   
            4d 8b 09 
            89 44   
            24 20
            4c 8d   
            05 .. 
            .. .. ..
            ba 01   
            00 00 00
            33 c9   

            e8 ..   
            .. .. ..
        ''',
        # Make a few nops.
        new_code = '''
            49 83   
            79 18 10
            72 03   
            4d 8b 09
            89 44   
            24 20
            4c 8d   
            05 .. 
            .. .. ..
            ba 01   
            00 00 00
            33 c9   
        ''' + NOP * 5,
        ),
    
    Binary_Patch(
        file = Settings.X4_exe_name,
        # Call is at the end of this block, since after the call is code
        # ghidra didn't understand, and so may be hard to pick out addresses.
        ref_code = '''
            48 83   
            7b 48 10
            48 8d   
            53 30
            72 03   
            48 8b 12
            48 8d   
            0d .. 
            .. .. ..

            e8 .. 
            .. .. ..

            bf 04   
            00 00 00
            e9 89   
            00 00 00
        ''',
        # Make a few nops.
        new_code = ''' 
            48 83   
            7b 48 10
            48 8d   
            53 30
            72 03   
            48 8b 12
            48 8d   
            0d .. 
            .. .. ..
        ''' + NOP * 5,
        ),
    ]

    Apply_Binary_Patch_Group(patches)
    return



@Transform_Wrapper()
def Remove_Modified():
    '''
    Partially removes the modified flag, eg. from the top menu.
    Written for Windows v3.10 exe.
    '''

    '''
    Of interest is the GetModified function, and a related FUN_140739170
    that it calls. The latter checks global DAT_1429efd70, returns it
    if 1, else checks a variety of other globals for conditions to
    also return a 1, until finally just returning DAT_1429efd70 (presumably
    0 at this point, though maybe is could be 2+?).

    There are 10 calls to FUN_140739170, so editing it should affect
    more places than GetModified, for better or worse.

    Code to look at:  loads DAT_1429efd70 into RAX (64-bit reg), then
    compares low half (EAX) to 1, goes down to the extra logic, and
    returns the RAX value if 1.
    On the other path, if conditions check out, it loads 1 into EAX
    and returns.  (A move into EAX clears the high part of RAX.)

    Can replace the RAX load with loading 0 and see what happens.
    (Or is just loading EAX sufficient?)
    ` 140739170 48 83      SUB     RSP,0x28
    `           ec 28
    ` 140739174 48 8b      MOV     RAX,qword ptr [DAT_1429efd70]     = ??
    `           05 f5 
    `           6b 2b 02
    ` 14073917b 83 f8 01   CMP     EAX,0x1
    ` 14073917e 75 05      JNZ     LAB_140739185
    ` 140739180 48 83      ADD     RSP,0x28
    `           c4 28
    ` 140739184 c3         RET
    `                   LAB_140739185                     XREF[1]: 14073917e(j)  
    ` 140739185 48 89      MOV     qword ptr [RSP + local_8],RBX
    `           5c 24 20

    Move 0 into EAX (will need a couple extra nops):
        b8 00 00 00 00

    Test result: didn't seem to work.
    Maybe try editing IsGameModified directly.

    
    ` 140182ec0 48 83      SUB     RSP,0x28
    `           ec 28
    ` 140182ec4 e8 a7      CALL    FUN_140739170
    `           62 5b 00
    ` 140182ec9 83 f8 07   CMP     EAX,0x7
    ` 140182ecc 77 11      JA      LAB_140182edf
    ` 140182ece b9 a1      MOV     ECX,0xa1
    `           00 00 00
    ` 140182ed3 0f a3 c1   BT      ECX,EAX
    ` 140182ed6 73 07      JNC     LAB_140182edf
    ` 140182ed8 32 c0      XOR     AL,AL
    ` 140182eda 48 83      ADD     RSP,0x28
    `           c4 28
    ` 140182ede c3         RET
    `                      LAB_140182edf
    ` 140182edf b0 01      MOV     AL,0x1
    ` 140182ee1 48 83      ADD     RSP,0x28
    `           c4 28
    ` 140182ee5 c3         RET

    Can change the latter b0 01 to b0 00.
    Test result: success, modified menu tag is gone.

    '''

    
    patches = [
    
        ## FUN_140739170, not much luck.
        #Binary_Patch(
        #file = Settings.X4_exe_name,
        #ref_code = '''
        #48 83   
        #ec 28
        #
        #48 8b   
        #05 .. 
        #.. .. ..
        #
        #83 f8 01
        #75 05   
        #48 83   
        #c4 28
        #c3      
        #48 89 
        #5c 24 20
        #''',
        ## Replace the middle bit, pad with a couple nops.
        #new_code = ''' 
        #48 83   
        #ec 28
        #
        #b8 00 
        #00 00 
        #00 90 90
        #''',
        #),
    
        # IsGameModified edit
        Binary_Patch(
        file = Settings.X4_exe_name,
        ref_code = '''
        83 f8 07
        77 11   
        b9 a1   
        00 00 00
        0f a3 c1
        73 07   
        32 c0   
        48 83   
        c4 28
        c3      
        
        b0 01   
        48 83   
        c4 28
        c3      
        ''',
        new_code = ''' 
        83 f8 07
        77 11   
        b9 a1   
        00 00 00
        0f a3 c1
        73 07   
        32 c0   
        48 83   
        c4 28
        c3      
        
        b0 00   
        48 83   
        c4 28
        c3      
        ''',
        ),
    ]
    
    Apply_Binary_Patch_Group(patches)
    return