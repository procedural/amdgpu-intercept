#!/usr/bin/env python

CopyRight = '''
/*
 * Copyright 2015 Advanced Micro Devices, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * on the rights to use, copy, modify, merge, publish, distribute, sub
 * license, and/or sell copies of the Software, and to permit persons to whom
 * the Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice (including the next
 * paragraph) shall be included in all copies or substantial portions of the
 * Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHOR(S) AND/OR THEIR SUPPLIERS BE LIABLE FOR ANY CLAIM,
 * DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
 * OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
 * USE OR OTHER DEALINGS IN THE SOFTWARE.
 *
 */
'''

import sys
import re


class Field:
    def __init__(self, reg, s_name):
        self.s_name = s_name
        self.name = strip_prefix(s_name)
        self.values = []
        self.varname_values = '%s__%s__values' % (reg.r_name.lower(), self.name.lower())

class Reg:
    def __init__(self, r_name):
        self.r_name = r_name
        self.name = strip_prefix(r_name)
        self.fields = []
        self.varname_fields = '%s__fields' % self.r_name.lower()
        self.own_fields = True


def strip_prefix(s):
    '''Strip prefix in the form ._.*_, e.g. R_001234_'''
    return s[s[2:].find('_')+3:]


def parse(filename):
    stream = open(filename)
    regs = []
    packets = []

    for line in stream:
        if not line.startswith('#define '):
            continue

        line = line[8:].strip()

        if line.startswith('R_'):
            reg = Reg(line.split()[0])
            regs.append(reg)

        elif line.startswith('S_'):
            field = Field(reg, line[:line.find('(')])
            reg.fields.append(field)

        elif line.startswith('V_'):
            field.values.append(line.split()[0])

        elif line.startswith('PKT3_') and line.find('0x') != -1 and line.find('(') == -1:
            packets.append(line.split()[0])

    # Copy fields to indexed registers which have their fields only defined
    # at register index 0.
    # For example, copy fields from CB_COLOR0_INFO to CB_COLORn_INFO, n > 0.
    match_number = re.compile('[0-9]+')
    reg_dict = dict()

    # Create a dict of registers with fields and '0' in their name
    for reg in regs:
        if len(reg.fields) and reg.name.find('0') != -1:
            reg_dict[reg.name] = reg

    # Assign fields
    for reg in regs:
        if not len(reg.fields):
            reg0 = reg_dict.get(match_number.sub('0', reg.name))
            if reg0 != None:
                reg.fields = reg0.fields
                reg.varname_fields = reg0.varname_fields
                reg.own_fields = False

    return (regs, packets)


def write_tables(tables):
    regs = tables[0]
    packets = tables[1]

    print '/* This file is autogenerated by sid_tables.py from sid.h. Do not edit directly. */'
    print
    print CopyRight.strip()
    print '''
#ifndef SID_TABLES_H
#define SID_TABLES_H

struct si_enum {
        unsigned value;
        const char* name;
};

struct si_field {
        const char *name;
        unsigned mask;
        unsigned num_values;
        struct si_enum *values;
};

struct si_reg {
        const char *name;
        unsigned offset;
        unsigned num_fields;
        const struct si_field *fields;
};

struct si_packet3 {
        const char *name;
        unsigned op;
};
'''

    print 'static const struct si_packet3 packet3_table[] = {'
    for pkt in packets:
        print '\t{"%s", %s},' % (pkt[5:], pkt)
    print '};'
    print

    for reg in regs:
        if len(reg.fields) and reg.own_fields:
            for field in reg.fields:
                if len(field.values):
                    print 'static si_enum %s[] = {' % (field.varname_values)
                    for value in field.values:
                        print '\t{%s, "%s"},' % (value, strip_prefix(value))
                    print '};'
                    print

            print 'static const struct si_field %s[] = {' % (reg.varname_fields)
            for field in reg.fields:
                if len(field.values):
                    print '\t{"%s", %s(~0u), ARRAY_SIZE(%s), %s},' % (field.name,
                        field.s_name, field.varname_values, field.varname_values)
                else:
                    print '\t{"%s", %s(~0u)},' % (field.name, field.s_name)
            print '};'
            print

    print 'static const struct si_reg reg_table[] = {'
    for reg in regs:
        if len(reg.fields):
            print '\t{"%s", %s, ARRAY_SIZE(%s), %s},' % (reg.name, reg.r_name,
                reg.varname_fields, reg.varname_fields)
        else:
            print '\t{"%s", %s},' % (reg.name, reg.r_name)
    print '};'
    print
    print '#endif'


def main():
    tables = []
    for arg in sys.argv[1:]:
        tables.extend(parse(arg))
    write_tables(tables)


if __name__ == '__main__':
    main()
