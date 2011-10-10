# ------------------------------------------------------------------------------
import difflib

# ------------------------------------------------------------------------------
class HtmlDiff:
    '''This class allows to compute differences between two versions of some
       HTML chunk.'''
    insertStyle = 'color: blue; cursor: help'
    deleteStyle = 'color: red; text-decoration: line-through; cursor: help'

    def __init__(self, old, new,
                 insertMsg='Inserted text', deleteMsg='Deleted text',
                 insertCss=None, deleteCss=None, diffRatio=0.7):
        # p_old and p_new are strings containing chunks of HTML.
        self.old = old.strip()
        self.new = new.strip()
        # Every time an "insert" or "delete" difference will be detected from
        # p_old to p_new, the impacted chunk will be surrounded by a tag that
        # will get, respectively, a 'title' attribute filled p_insertMsg or
        # p_deleteMsg. The message will give an explanation about the change
        # (who made it and at what time, for example).
        self.insertMsg = insertMsg
        self.deleteMsg = deleteMsg
        # This tag will get a CSS class p_insertCss or p_deleteCss for
        # highlighting the change. If no class is provided, default styles will
        # be used (see HtmlDiff.insertStyle and HtmlDiff.deleteStyle).
        self.insertCss = insertCss
        self.deleteCss = deleteCss
        # The diff algorithm of this class will need to identify similarities
        # between strings. Similarity ratios will be computed by using method
        # difflib.SequenceMatcher.ratio (see m_isSimilar below). Strings whose
        # comparison will produce a ratio  above p_diffRatio will be considered
        # as similar.
        self.diffRatio = diffRatio

    def getModifiedChunk(self, seq, type, sep):
        '''p_sep.join(p_seq) is a chunk that was either inserted
           (p_type='insert') or deleted (p_type='delete'). This method will
           surround this part with a div or span tag that will get some CSS
           class allowing to highlight the difference.'''
        if sep == '\n': tag = 'div'
        else: tag = 'span'
        exec 'msg = self.%sMsg' % type
        exec 'cssClass = self.%sCss' % type
        if cssClass:
            style = 'class="%s"' % cssClass
        else:
            exec 'style = self.%sStyle' % type
            style = 'style="%s"' % style
        return '<%s %s title="%s">%s</%s>' % (tag,style,msg,sep.join(seq),tag)

    def getStringDiff(self, old, new):
        '''Identifies the differences between strings p_old and p_new by
           computing:
           * i = the end index of the potential common starting part (if no
                 common part is found, i=0);
           * jo = the start index in p_old of the potential common ending part;
           * jn = the start index in p_new of the potential common ending part.
        '''
        # Compute i
        i = -1
        diffFound = False
        while not diffFound:
            i += 1
            if old[i] != new[i]: diffFound = True
        # Compute jo and jn
        jo = len(old)
        jn = len(new)
        diffFound = False
        while not diffFound:
            if (jo == i) or (jn == i):
                # We have reached the end of substring old[i:] or new[i:]
                jo -=1
                jn -= 1
                break
            jo -= 1
            jn -= 1
            if old[jo] != new[jn]: diffFound=True
        return i, jo+1, jn+1

    def isSimilar(self, s1, s2):
        '''Returns True if strings p_s1 and p_s2 can be considered as
           similar.'''
        ratio = difflib.SequenceMatcher(a=s1.lower(), b=s2.lower()).ratio()
        return ratio > self.diffRatio

    def getSeqDiff(self, seqA, seqB):
        '''p_seqA and p_seqB are lists of strings. Here we will try to identify
           similarities between strings from p_seqA and p_seqB, and return a
           list of differences between p_seqA and p_seqB, where each element
           is a tuple (action, data).
           * If p_action is "delete", data is a sublist of p_seqA with lines
             considered as not included anymore in p_seqB;
           * If p_action is "replace", data is a tuple (lineA, lineB) containing
             one line from p_seqA and one from p_seqB considered as similar;
           * If p_action is "insert", data is a sublist of p_seqB with lines
             considered as not included in p_seqA.
        '''
        res = []
        i = j = k = 0
        deleted = []
        # Scan every string from p_seqA and try to find a similar string in
        # p_seqB.
        while i < len(seqA):
            if k == len(seqB):
                # We have already "consumed" every string from p_seqB. Remaining
                # strings from p_seqA must now be considered has having been
                # deleted.
                if deleted: res.append( ('delete', deleted) )
                res.append( ('delete', seqA[i:]) )
                break
            similarFound = False
            for j in range(k, len(seqB)):
                if self.isSimilar(seqA[i], seqB[j]):
                    similarFound = True
                    if deleted:
                        # Dump first the strings flagged as deleted.
                        res.append( ('delete', deleted) )
                        deleted = []
                    # Strings between indices k and j in p_seqB must be
                    # considered as inserted, because no similar line exists
                    # in p_seqA.
                    if k < j:
                        res.append( ('insert', seqB[k:j]) )
                    # Similar strings are appended in a 'replace' entry
                    res.append(('replace', (seqA[i], seqB[j])))
                    k = j+1
                    break
            if not similarFound:
                # Add to list of deleted lines.
                deleted.append(seqA[i])
            i += 1
        # Consider any "unconsumed" line from p_seqB as being inserted.
        if deleted: res.append( ('delete', deleted) )
        if k < len(seqB): res.append( ('insert', seqB[k:]) )
        return res

    def getHtmlDiff(self, old, new, sep):
        '''Returns the differences between p_old and p_new. Result is a string
           containing the comparison in HTML format. p_sep is used for turning
           p_old and p_new into sequences.'''
        res = []
        a = old.split(sep)
        b = new.split(sep)
        matcher = difflib.SequenceMatcher()
        matcher.set_seqs(a,b)
        for action, i1, i2, j1, j2 in matcher.get_opcodes():
            if action == 'equal':
                toAdd = sep.join(a[i1:i2])
            elif action == 'insert':
                toAdd = self.getModifiedChunk(b[j1:j2], action, sep)
            elif action == 'delete':
                toAdd = self.getModifiedChunk(a[i1:i2], action, sep)
            elif action == 'replace':
                if sep == '\n':
                    # We know that some lines have been replaced from a to b. By
                    # identifying similarities between those lines, consider
                    # some as having been deleted, modified or inserted.
                    toAdd = ''
                    for sAction, data in self.getSeqDiff(a[i1:i2], b[j1:j2]):
                        if sAction in ('insert', 'delete'):
                            toAdd += self.getModifiedChunk(data, sAction, sep)
                        elif sAction == 'replace':
                            lineA, lineB = data
                            # Investigate further here and explore differences
                            # at the *word* level between lineA and lineB. As a
                            # preamble, and in order to restrict annoyances due
                            # to the presence of XHTML tags, we will compute
                            # start and end parts wich are similar between lineA
                            # and lineB: they may correspond to opening and
                            # closing XHTML tags.
                            i, ja, jb = self.getStringDiff(lineA, lineB)
                            diff = self.getHtmlDiff(lineA[i:ja],lineB[i:jb],' ')
                            toAdd += lineB[:i] + diff + lineB[jb:]
                else:
                    if ((i2-i1) == 1) and (a[i1] == ''):
                        # difflib has considered an empty char as 'removed' (?)
                        toAdd = ''
                    else:
                        toAdd = self.getModifiedChunk(a[i1:i2],'delete', sep)
                    toAdd += self.getModifiedChunk(b[j1:j2],'insert', sep)
            res.append(toAdd)
        return sep.join(res)

    def get(self):
        '''Produces the result.'''
        return self.getHtmlDiff(self.old, self.new, '\n')
# ------------------------------------------------------------------------------
