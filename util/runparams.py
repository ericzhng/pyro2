"""basic syntax of the parameter file is:

# simple parameter file

[driver]
nsteps = 100         ; comment
max_time = 0.25

[riemann]
tol = 1.e-10
max_iter = 10

[io]
basename = myfile_


The recommended way to use this is for the code to have a master list
of parameters and their defaults (e.g. _defaults), and then the
user can override these defaults at runtime through an inputs file.
These two files have the same format.

The calling sequence would then be:

  rp = RuntimeParameters()
  rp.load_params("_defaults")
  rp.load_params("inputs")

The parser will determine what datatype the parameter is (string,
integer, float), and store it in a RuntimeParameters object.
If a parameter that already exists is encountered a second time (e.g.,
there is a default value in _defaults and the user specifies a new
value in inputs), then the second instance replaces the first.

Runtime parameters can then be accessed via any module through the
get_param method:

  tol = rp.get_param('riemann.tol')

If the optional flag no_new=1 is set, then the load_params function
will not define any new parameters, but only overwrite existing ones.
This is useful for reading in an inputs file that overrides previously
read default values.

"""

import string
import re
from util import msg


# some utility functions to automagically determine what the data
# types are
def is_int(string):
    """ is the given string an interger? """
    try: int(string)
    except ValueError: return 0
    else: return 1

def is_float(string):
    """ is the given string a float? """
    try: float(string)
    except ValueError: return 0
    else: return 1


class RuntimeParameters:

    def __init__ (self):
        """
        Initialize a collection of runtime parameters.  This class
        holds a dictionary of the parameters, their comments, and keeps
        track of which parameters were actually used.
        """

        # keep track of the parameters and their comments 
        self.params = {}
        self.param_comments = {}

        # for debugging -- keep track of which parameters were
        # actually looked- up
        self.used_params = []

    def load_params(self, file, no_new=0):
        """
        Reads line from file and makes dictionary pairs from the data
        to store.

        Parameters
        ----------
        file : str
            The name of the file to parse
        no_new : int, optional
            If no_new = 1, then we don't add any new paramters to the
            dictionary of runtime parameters, but instead just override
            the values of existing ones.

        """

        # check to see whether the file exists
        try: f = open(file, 'r')
        except IOError:
            msg.fail("ERROR: parameter file does not exist: %s" % (file))

        # we could use the ConfigParser, but we actually want to
        # have our configuration files be self-documenting, of the
        # format key = value ; comment
        sec = re.compile(r'^\[(.*)\]')
        eq = re.compile(r'^([^=#]+)=([^;]+);{0,1}(.*)')

        for line in f.readlines():

            if sec.search(line): 
                lbracket, section, rbracket = sec.split(line)
                section = string.lower(section.strip())
            
            elif eq.search(line):
                left, item, value, comment, right = eq.split(line) 
                item = string.lower(item.strip())

                # define the key
                key = section + "." + item
            
                # if we have no_new = 1, then we only want to override existing
                # key/values
                if (no_new):
                    if (not key in self.params.keys()):
                        msg.warning("warning, key: %s not defined" % (key))
                        continue

                # check in turn whether this is an interger, float, or string
                if (is_int(value)):
                    self.params[key] = int(value)
                elif (is_float(value)):
                    self.params[key] = float(value)
                else:
                    self.params[key] = value.strip()

                # if the comment already exists (i.e. from reading in
                # _defaults) and we are just resetting the value of
                # the parameter (i.e.  from reading in inputs), then
                # we don't want to destroy the comment
                if comment.strip() == "":
                    try:
                        comment = self.param_comments[key]
                    except KeyError:
                        comment = ""
                    
                self.param_comments[key] = comment.strip()


    def command_line_params(self, cmd_strings):
        """
        finds dictionary pairs from a string that came from the
        commandline.  Stores the parameters in globalParams only if they 
        already exist.
        
        we expect things in the string in the form:
         ["sec.opt=value",  "sec.opt=value"]
        with each opt an element in the list

        Parameters
        ----------
        cmd_strings : list
            The list of strings containing runtime parameter pairs            

        """

        for item in cmd_strings:

            # break it apart
            key, value = item.split("=")
            
            # we only want to override existing keys/values
            if (not key in self.params.keys()):
                msg.warning("warning, key: %s not defined" % (key))
                continue

            # check in turn whether this is an interger, float, or string
            if (is_int(value)):
                self.params[key] = int(value)
            elif (is_dloat(value)):
                self.params[key] = float(value)
            else:
                self.params[key] = value.strip()

    
    def get_param(self, key):
        """
        returns the value of the runtime parameter corresponding to the
        input key
        """

        if self.params == {}:
            msg.warning("WARNING: runtime parameters not yet initialized")
            self.load_params("_defaults")

        # debugging
        if not key in self.used_params:
            self.used_params.append(key)
        
        if key in self.params.keys():
            return self.params[key]
        else:
            msg.fail("ERROR: runtime parameter %s not found" % (key))
        

    def print_unused_params(self):
        """
        Print out the list of parameters that were defined by never used
        """
        for key in self.params.keys():
            if not key in self.used_params:
                msg.warning("parameter %s never used" % (key))
    

    def print_all_params(self):
        """
        Print out all runtime parameters and their values
        """
        keys = self.params.keys()
        keys.sort()

        for key in keys:
            print key, "=", self.params[key]

        print " "
    

    def print_paramfile(self):
        """
        Create a file, inputs.auto, that has the structure of a pyro
        inputs file, with all known parameters and values
        """

        keys = self.params.keys()
        keys.sort()

        try: f = open('inputs.auto', 'w')
        except IOError:
            msg.fail("ERROR: unable to open inputs.auto")


        f.write('# automagically generated parameter file\n')
    
        currentSection = " "

        for key in keys:
            parts = string.split(key, '.')
            section = parts[0]
            option = parts[1]

            if (section != currentSection):
                currentSection = section
                f.write('\n')
                f.write('[' + section + ']\n')

            if (isinstance(self.params[key], int)):
                value = '%d' % self.params[key]
            elif (isinstance(self.params[key], float)):
                value = '%f' % self.params[key]
            else:
                value = self.params[key]

        
            if (self.param_comments[key] != ''):
                f.write(option + ' = ' + value + '       ; ' + self.param_comments[key] + '\n')
            else:
                f.write(option + ' = ' + value + '\n')

        f.close()
     
    
if __name__== "__main__":
    rp = RuntimeParameters()
    rp.load_params("inputs.test")
    rp.print_paramfile()



    



