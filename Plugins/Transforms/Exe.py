'''
Transforms to the raw exe binary.
'''
__all__ = [    
    'Remove_Modified',
    'Remove_Sig_Errors',
    'High_Precision_Systemtime',
    #'Remove_Workshop_Tool_Dependency_Check',
    ]

from datetime import datetime

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
    ` 140182ec9 83 f8 07   CMP     EAX,0x7     ; 0x9 in 3.2b2
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

    Update: in 3.2b2, a couple insts changed:
        `  83 f8 07   CMP     EAX,0x7
        `  77 11      JA      LAB_140182edf
        `  b9 a1      MOV     ECX,0xa1
        `  00 00 00
    to    
        `  83 f8 09   CMP     EAX,0x9
        `  77 11      JA      LAB_140182edf
        `  b9 a1      MOV     ECX,0x2a1
        `  02 00 00
    Assuming these values are volatile, can wildcard them.
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
        83 f8 ..
        77 11   
        b9 a1   
        .. 00 00
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
        83 f8 ..
        77 11   
        b9 a1   
        .. 00 00
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


@Transform_Wrapper()
def High_Precision_Systemtime(
        scaling_power = 0,
    ):
    '''
    Changes the player.systemtime property to use a higher precision
    underlying timer, where a printed "second" will actually have
    a stepping of 100 ns. Useful for performance profiling of code blocks.

    Underlying precision comes from Windows GetSystemTimePreciseAsFileTime,
    which is presumably as accurate as its 100 ns unit size.

    Time will roll over roughly every 7 minutes, going back to 1970,
    due to limitations of the underlying string format functions.

    For short measurements, roughly 8 ms or less, just the lower part
    of the timer may be used, up to hour: player.systemtime.{'%H,%M,%S'}.
    For longer measurements, this needs to expand into the day field
    and account for leap years: player.systemtime.{'%G,%j,%H,%M,%S'}.

    As these are strings, conversion to an actual time relies on
    processing outside of the normal script engine, eg. in lua.
    Note: 1972 was a leap year, and every 4 after, which needs to be
    considered for full accuracy.
    '''

    '''
    In quick summary:
    - player.systemtime.{$format} is implemented using a c++ strftime call.
    - The underlying timer digs down to the windows GetSystemTimeAsFiletime
      or GetSystemTimePreciseAsFileTime functions (former used if the latter
      is not available).
    - The above return a 64-bit value of time since 1601, in 100 ns units.
    - This time is adjusted to be related to 1970, then converted to seconds.
    - This transform will undo (partially) the second conversion, so the
      basic units are still something smaller.

    One quirk is that strftime is limited to below year 3000 (with a check
    in the code). By bypassing that check, results may be a little wacky.

    Relevant ghidra decompiled code block:
    common_timespec_get<struct__timespec64>

        ` local_res8[0] = 0;
        ` __acrt_GetSystemTimePreciseAsFileTime(local_res8);
        // Result ~= (2020 - 1601) * 365.25 * 24 * 60 * 60 * 10000000 = 0x_01d5_c328_c811_9000

        ` local_res8[0] = local_res8[0] + -0x19db1ded53e8000;
        // Adjusts 1600 to 1970.
        // 0x19d_b1de_d53e_8000 = 134774 days, just about 369 years.
        // Result ~= 0x_0038_1149_f2d3_1000 = 15,781,608,000,000,000

        ` lVar2 = SUB168(SEXT816(-0x29406b2a1a85bd43) * SEXT816(local_res8[0]) >> 0x40,0) + local_res8[0];
        // 0x29406b2a1a85bd43 = 2,972,493,582,642,298,179
        // SEXT816/SUB168/>>0x40 is basically saying this is a full
        // signed multiply, dropping the low 64-bits.
        // eg.:
        //   lVar2 = (-0x0.29406b2a1a85bd43 * local_res8[0]) + local_res8[0];
        // or
        //   lVar2 = local_res8[0] * (1 - 0.1611392)
        // Result ~= 0x_5e10_d2a0 = 1,578,160,800

        ` lVar2 = (lVar2 >> 0x17) - (lVar2 >> 0x3f);
        // Works with the above to finish conversion of 100ns to s units.
        // example: (1 * (1 - 0.1611392)) >> 23  = 0.0000001
        // The last >>0x3f isn't very significant.
        // Result ~= 0x_5e10_d2a0 = 1,578,160,800

        ` if (lVar2 < 0x793407000) {
        // 0x7_9340_7000 = 32,535,244,800 seconds, roughly 1030 years.
        // Compares to year 3000 (since relative to year 1970),
        // rejecting anything over (goes to an error return code).

        `   *(longlong *)param_1 = lVar2;
        `   *(int *)(param_1 + 8) = ((int)local_res8[0] + (int)lVar2 * -10000000) * 100;
        `   return 1;
        // Stores the remainder as nanoseconds.
        // param_1[0] will hold the result in seconds, 
        // param_1[1] will hold the remainder.


    Roll over and the year-3000 limit:
        At some point, the time will grow to the point it hits the 3000-year
        check. This could potentially be avoided with bit manipulation to
        keep the range of the value going into the check below 0x7_9340_7000,
        eg. AND with 0x3_FFFF_FFFF.
        Alternatively, perform a left shift then right shift (not arithmatic),
        to clear out the high ~32 bits (can keep up to 34, but not important).
        Or, more simply, changed code to only return the low half of the
        64-bit timer.


    Machine code section:
        // Okay to leave this alone.
      ` 14116f2b1 48 b9      MOV     param_1,-0x19db1ded53e8000
      `           00 80 
      `           c1 2a 
      `           21 4e 
      `           62 fe
      ` 14116f2bb 4c 03 c1   ADD     R8,param_1
        // Set to 0; no adjustment.
      ` 14116f2be 48 b8      MOV     RAX,-0x29406b2a1a85bd43
      `           bd 42 
      `           7a e5 
      `           d5 94 
      `           bf d6
      ` 14116f2c8 49 f7 e8   IMUL    R8
      ` 14116f2cb 49 03 d0   ADD     param_2,R8

        // Remove this shift (just >>0).
      ` 14116f2ce 48 c1      SAR     param_2,0x17
      `           fa 17
      ` 14116f2d2 48 8b c2   MOV     RAX,param_2
        // Leave alone
      ` 14116f2d5 48 c1      SHR     RAX,0x3f
      `           e8 3f
        // For some reason this is actually a subtract?
      ` 14116f2d9 48 03 d0   ADD     param_2,RAX

      // Setup for the 3k check; leave alone.
      ` 14116f2dc 48 b8      MOV     RAX,0x793406fff
      `           ff 6f 
      `           40 93 
      `           07 00 
      `           00 00

    Edits to make

    Note: with no scaling, this will rollover every 429 seconds (7 minutes).
        
        // High part of param_2 should be 0, so SAR is fine.
        // (Note: if this works, don't even need a scaling_power.)
        48 c1      SAR     param_2, <scaling_power>
        fa ##
        // Can leave this as-is; should be very small.
        48 8b c2   MOV     RAX,param_2
        48 c1      SHR     RAX,0x3f
        e8 3f
        // This needs the EAX tweak to grab low, the only opcode edit.
        01 c2      ADD     param_2(low),EAX
        90         NOP


    '''

    # -Removed; with bit growth protection this stuff isn't needed.
    ## Determine the base time, roughly now, in 100 ns units.
    #since_1601 = -int((datetime.now() - datetime(1601,1,1)).total_seconds() * 10000000)
    ## This will pack to an 8 byte value. Reverse it for the assembly.
    #base_time_8b = Int_To_Hex_String(since_1601, 8, byteorder = 'little')
    #
    ## Encode the shift amount. Sanity check this.
    ## Around 20 is ~1 second; past that is probably a mistake.
    #if scaling_power > 24 or scaling_power < 0:
    #    raise Exception('Unexpected scaling_power')
    #shift_amount_1b = Int_To_Hex_String(scaling_power, 1, byteorder = 'little')
    #
    ## Test mode: try making minimal changes, that keep seconds close to 1/sec,
    ## time close to 1970 based.
    #if 0:
    #    # Note: this produces exactly the same hex value as original code.
    #    since_1970 = -int((datetime(1970,1,1) - datetime(1601,1,1)).total_seconds() * 10000000)
    #    base_time_8b = Int_To_Hex_String(since_1970, 8, byteorder = 'little')
    #    # 2^23 = 8.3 million; close to 10 million needed for seconds.
    #    shift_amount_1b = Int_To_Hex_String(23, 1, byteorder = 'little')

    
    patches = [
    
        Binary_Patch(
        file = Settings.X4_exe_name,
        ref_code = '''
        48 b9   
        00 80 
        c1 2a 
        21 4e 
        62 fe

        4c 03 c1

        48 b8   
        bd 42 
        7a e5 
        d5 94 
        bf d6

        49 f7 e8
        49 03 d0

        48 c1   
        fa 17

        48 8b c2

        48 c1   
        e8 3f

        48 03 d0
        48 b8   
        ff 6f 
        40 93 
        07 00 
        00 00
        ''',
        new_code = '''
        48 b9   
        00 80 
        c1 2a 
        21 4e 
        62 fe

        4c 03 c1

        48 b8   
        00 00 
        00 00 
        00 00 
        00 00

        49 f7 e8
        49 03 d0

        48 c1   
        fa 00

        48 8b c2

        48 c1   
        e8 3f

        01 c2
        90

        48 b8   
        ff 6f 
        40 93 
        07 00 
        00 00
        ''',
        ),
    ]
    
    Apply_Binary_Patch_Group(patches)
    return


# -Removed; no longer needed after tool update.
#@Transform_Wrapper()
#def Remove_Workshop_Tool_Dependency_Check():
#    '''
#    From the steam workshop upload tool, remove the dependency check that
#    requires dependencies start with "ws_" and be present on the workshop.
#    Experimental; developed to allow dependnencies on egosoft dlc.
#
#    Put WorkshopTool.exe in the main x4 folder, so the customizer
#    can find it, then copy the modified version back to the x tools dir.
#    '''
#    '''
#    Can just skip over the error handler for this case:
#
#    uVar17 = FUN_1400e7c50((longlong)local_5c98);
#    if ((char)uVar17 == '\0') {
#      pwVar51 = L"ERROR: There are dependencies on non-Workshop extensions\n";
#      goto LAB_1400e779f;
#    }
#
#    ` 1400e5715 48 8d      LEA     param_1=>local_5c98,[RBP + 0x80]
#    `           8d 80 
#    `           00 00 00
#    ` 1400e571c e8 2f      CALL    FUN_1400e7c50                     ulonglong FUN_1400e7c5
#    `           25 00 00
#    ` 1400e5721 84 c0      TEST    AL,AL
#    ` 1400e5723 75 0c      JNZ     LAB_1400e5731
#    ` 1400e5725 48 8d      LEA     param_2,[u_ERROR:_There_are_depe  = u"ERROR: There are d
#    `           15 c4 
#    `           92 03 00
#    ` 1400e572c e9 6e      JMP     LAB_1400e779f
#    `           20 00 00
#
#
#    Convert it to nops.
#    '''
#    patch = Binary_Patch(
#        file = 'WorkshopTool.exe',
#        ref_code = '''
#        48 8d   
#        8d .. 
#        .. .. ..
#        e8 ..   
#        .. .. ..
#        84 c0   
#        75 0c   
#        48 8d   
#        .. .. 
#        .. .. ..
#        e9 ..   
#        .. .. ..
#        ''',
#        # Keep the lea and call, nop the rest.
#        new_code = '''
#        48 8d   
#        8d .. 
#        .. .. ..
#        e8 ..   
#        .. .. ..
#        ''' + NOP * 16,
#        )
#    
#    Apply_Binary_Patch(patch)
#    return