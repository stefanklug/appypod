# ------------------------------------------------------------------------------
import re, difflib

# ------------------------------------------------------------------------------
innerDiff = re.compile('<span name="(insert|delete)".*? title="(.*?)">' \
                       '(.*?)</span>')

# ------------------------------------------------------------------------------
class Merger:
    '''This class allows to merge 2 lines of text, each containing inserts and
       deletions.'''
    def __init__(self, lineA, lineB, previousDiffs, differ):
        # lineA comes "naked": any diff previously found on it was removed from
        # it (ie, deleted text has been completely removed, while inserted text
        # has been included, but without its surrounding tag). Info about
        # previous diffs is kept in a separate variable "previousDiffs".
        self.lineA = lineA
        self.previousDiffs = previousDiffs
        # Differences between lineA and lineB have just been computed and are
        # included (within inner tags) in lineB. We will compute their position
        # in self.newDiffs (see below).
        self.lineB = lineB
        self.newDiffs = self.computeNewDiffs()
        # We choose to walk within self.lineB. We will keep in self.i our
        # current position within self.lineB.
        self.i = 0
        # The delta index that must be applied on previous diffs
        self.deltaPrevious = 0
        # A link to the caller HtmlDiff class.
        self.differ = differ
        # While "consuming" diffs (see m_getNextDiff), keep here every message
        # from every diff.
        self.messages = [self.differ.complexMsg]

    def computeNewDiffs(self):
        '''lineB may include inner "insert" and/or tags. This function
           detects them.'''
        i = 0
        res = []
        while i < len(self.lineB):
            match = innerDiff.search(self.lineB, i)
            if not match: break
            res.append(match)
            i = match.end()
        return res

    def getNextDiff(self):
        '''During the merging process on self.lineB, what next diff to
           "consume"? An old one? A new one?'''
        # No more diff ?
        if not self.previousDiffs and not self.newDiffs:
            return None, None, None
        # No more new diff ?
        if not self.newDiffs:
            diff = self.previousDiffs[0]
            del self.previousDiffs[0]
            return diff, diff.start() + self.deltaPrevious, True
        # No more previous diff ?
        if not self.previousDiffs:
            diff = self.newDiffs[0]
            del self.newDiffs[0]
            return diff, diff.start(), False
        # At least one more new and previous diff. Which one to consume?
        previousDiff = self.previousDiffs[0]
        newDiff = self.newDiffs[0]
        previousDiffIndex = previousDiff.start() + self.deltaPrevious
        newDiffIndex = newDiff.start()
        if previousDiffIndex <= newDiffIndex:
            # Previous wins
            del self.previousDiffs[0]
            return previousDiff, previousDiffIndex, True
        else:
            # New wins
            del self.newDiffs[0]
            return newDiff, newDiffIndex, False

    def manageOverlaps(self):
        '''We have detected that changes between lineA and lineB include
           overlapping inserts and deletions. Our solution: to remember names
           of editors and return the whole line in a distinct colour, where
           we (unfortunately) can't distinguish editors's specific updates.'''
        # First, get a "naked" version of self.lineB, without the latest
        # updates.
        res = self.lineB
        for diff in self.newDiffs:
            res = self.differ.applyDiff(res, diff)
        # Construct the message explaining the series of updates.
        # self.messages already contains messages from the "consumed" diffs
        # (see m_getNextDiff).
        for type in ('previous', 'new'):
            exec 'diffs = self.%sDiffs' % type
            for diff in diffs:
                self.messages.append(diff.group(2))
        msg = ' -=- '.join(self.messages)
        return self.differ.getModifiedChunk(res, 'complex', '\n', msg=msg)

    def merge(self):
        '''Merges self.previousDiffs into self.lineB.'''
        res = ''
        diff, diffStart, isPrevious = self.getNextDiff()
        if diff: self.messages.append(diff.group(2))
        while diff:
            # Dump the part of lineB between self.i and diffStart
            res += self.lineB[self.i:diffStart]
            self.i = diffStart
            # Dump the diff
            res += diff.group(0)
            if isPrevious:
                if diff.group(1) == 'insert':
                    # Check if the inserted text is still present in lineB
                    if self.lineB[self.i:].startswith(diff.group(3)):
                        # Yes. Go ahead within lineB
                        self.i += len(diff.group(3))
                    else:
                        # The inserted text can't be found as is in lineB.
                        # Must have been (partly) re-edited or removed.
                        return self.manageOverlaps()
            else:
                # Update self.i
                self.i += len(diff.group(0))
                # Because of this new diff, all indexes computed on lineA are
                # now wrong because we express them relative to lineB. So:
                # update self.deltaPrevious to take this into account.
                self.deltaPrevious += len(diff.group(0))
                if diff.group(1) == 'delete':
                    # The indexes in lineA do not take the deleted text into
                    # account, because it wasn't deleted at this time. So remove
                    # from self.deltaPrevious the length of removed text.
                    self.deltaPrevious -= len(diff.group(3))
            # Load next diff
            diff, diffStart, isPrevious = self.getNextDiff()
            if diff: self.messages.append(diff.group(2))
        # Dump the end of self.lineB if not completely consumed
        if self.i < len(self.lineB):
            res += self.lineB[self.i:]
        return res

# ------------------------------------------------------------------------------
class HtmlDiff:
    '''This class allows to compute differences between two versions of some
       HTML chunk.'''
    insertStyle = 'color: blue; cursor: help'
    deleteStyle = 'color: red; text-decoration: line-through; cursor: help'
    complexStyle = 'color: purple; cursor: help'

    def __init__(self, old, new,
                 insertMsg='Inserted text', deleteMsg='Deleted text',
                 complexMsg='Multiple inserts and/or deletions',
                 insertCss=None, deleteCss=None, complexCss=None,
                 insertName='insert', deleteName='delete',
                 complexName='complex', diffRatio=0.7):
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
        self.complexMsg = complexMsg
        # This tag will get a CSS class p_insertCss or p_deleteCss for
        # highlighting the change. If no class is provided, default styles will
        # be used (see HtmlDiff.insertStyle and HtmlDiff.deleteStyle).
        self.insertCss = insertCss
        self.deleteCss = deleteCss
        self.complexCss = complexCss
        # This tag will get a "name" attribute whose content will be
        # p_insertName or p_deleteName
        self.insertName = insertName
        self.deleteName = deleteName
        self.complexName = complexName
        # The diff algorithm of this class will need to identify similarities
        # between strings. Similarity ratios will be computed by using method
        # difflib.SequenceMatcher.ratio (see m_isSimilar below). Strings whose
        # comparison will produce a ratio above p_diffRatio will be considered
        # as similar.
        self.diffRatio = diffRatio
        # Some computed values
        for tag in ('div', 'span'):
            for type in ('insert', 'delete', 'complex'):
                setattr(self, '%s%sPrefix' % (tag, type.capitalize()),
                        '<%s name="%s"' % (tag, getattr(self, '%sName' % type)))

    def getModifiedChunk(self, seq, type, sep, msg=None):
        '''p_sep.join(p_seq) (if p_seq is a list) or p_seq (if p_seq is a
           string) is a chunk that was either inserted (p_type='insert') or
           deleted (p_type='delete'). It can also be a complex, partially
           managed combination of inserts/deletions (p_type='insert').
           This method will surround this part with a div or span tag that will
           get some CSS class allowing to highlight the update. If p_msg is
           given, it will be used instead of the default p_type-related message
           stored on p_self.'''
        # Will the surrouding tag be a div or a span?
        if sep == '\n': tag = 'div'
        else: tag = 'span'
        # What message wiill it show in its 'title' attribute?
        if not msg:
            exec 'msg = self.%sMsg' % type
        # What CSS class (or, if none, tag-specific style) will be used ?
        exec 'cssClass = self.%sCss' % type
        if cssClass:
            style = 'class="%s"' % cssClass
        else:
            exec 'style = self.%sStyle' % type
            style = 'style="%s"' % style
        # the 'name' attribute of the tag indicates the type of the update.
        exec 'tagName = self.%sName' % type
        # The idea is: if there are several lines, every line must be surrounded
        # by a tag. this way, we know that a surrounding tag can't span several
        # lines, which is a prerequisite for managing cumulative diffs.
        if sep == ' ':
            seq = sep.join(seq)
            sep = ''
        if isinstance(seq, basestring):
            return '%s<%s name="%s" %s title="%s">%s</%s>%s' % \
                   (sep, tag, tagName, style, msg, seq, tag, sep)
        else:
            res = ''
            for line in seq:
                res += '%s<%s name="%s" %s title="%s">%s</%s>%s' % \
                       (sep, tag, tagName, style, msg, line, tag, sep)
            return res

    def applyDiff(self, line, diff):
        '''p_diff is a regex containing an insert or delete that was found within
           line. This function applies the diff, removing or inserting the diff
           into p_line.'''
        # Keep content only for "insert" tags.
        content = ''
        if diff.group(1) == 'insert':
            content = diff.group(3)
        return line[:diff.start()] + content + line[diff.end():]

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
            if (i == len(old)) or (i == len(new)): break
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

    def splitTagAndContent(self, line):
        '''p_line is a XHTML tag with content. This method returns a tuple
           (startTag, content), where p_startTag is the isolated start tag and
           content is the tag content.'''
        i = line.find('>')+1
        return line[0:i], line[i:line.rfind('<')]

    def getLineAndType(self, line):
        '''p_line is a string that can already have been surrounded by an
           "insert" or "delete" tag. This is what we try to determine here.
           This method returns a tuple (type, line, innerDiffs, outerTag),
           where "type" can be:
           * "insert" if it has already been flagged as inserted;
           * "delete" if it has already been flagged as deleted;
           * None else;
           "line" holds the original parameter p_line, excepted:
           * if type="insert". In that case, the surrounding insert tag has been
             removed and placed into "outerTag" (the outer start tag to be more
             precise);
           * if inner diff tags (insert or delete) are found. In that case,
             - if inner "insert" tags are found, they are removed but their
               content is kept;
             - if inner "delete" tags are found, they are removed, content
               included;
             - "innerDiffs" holds the list of re.MatchObjects instances
               representing the found inner tags.
        '''
        if line.startswith(self.divDeletePrefix):
            return ('delete', line, None, None)
        if line.startswith(self.divInsertPrefix):
            # Return the line without the surrounding tag.
            action = 'insert'
            outerTag, line = self.splitTagAndContent(line)
        else:
            action = None
            outerTag = None
        # Replace found inner inserts with their content.
        innerDiffs = []
        while True:
            match = innerDiff.search(line)
            if not match: break
            # I found one.
            innerDiffs.append(match)
            line = self.applyDiff(line, match)
        return (action, line, innerDiffs, outerTag)

    def getSeqDiff(self, seqA, seqB):
        '''p_seqA and p_seqB are lists of strings. Here we will try to identify
           similarities between strings from p_seqA and p_seqB, and return a
           list of differences between p_seqA and p_seqB, where each element
           is a tuple (action, line).
           * If p_action is "delete", "line" is a line of p_seqA considered as
             not included anymore in p_seqB;
           * If p_action is "insert", "line" is a line of p_seqB considered as
             not included in p_seqA;
           * If p_action is "replace", "line" is a tuple
             (lineA, lineB, previousDiffsA) containing one line from p_seqA and
             one from p_seqB considered as similar. "previousDiffsA" contains
             potential previous inner diffs that were found (but extracted
             from, for comparison purposes) lineA.
        '''
        res = []
        i = j = k = 0
        # Scan every string from p_seqA and try to find a similar string in
        # p_seqB.
        while i < len(seqA):
            pastAction, lineA, innerDiffs, outerTag=self.getLineAndType(seqA[i])
            if pastAction == 'delete':
                # We will consider this line as "equal" because it already has
                # been noted as deleted in a previous diff.
                res.append( ('equal', seqA[i]) )
            elif k == len(seqB):
                # We have already "consumed" every string from p_seqB. Remaining
                # strings from p_seqA must be considered as deleted (or
                # sometimes equal, see above)
                if not pastAction: res.append( ('delete', seqA[i]) )
                else:
                    # 'insert': should not happen. The inserted line should also
                    # be found in seqB.
                    res.append( ('equal', seqA[i]) )
            else:
                # Try to find a line in seqB which is similar to lineA.
                similarFound = False
                for j in range(k, len(seqB)):
                    if self.isSimilar(lineA, seqB[j]):
                        similarFound = True
                        # Strings between indices k and j in p_seqB must be
                        # considered as inserted, because no similar line exists
                        # in p_seqA.
                        if k < j:
                            for line in seqB[k:j]: res.append(('insert', line))
                        # Similar strings are appended in a 'replace' entry,
                        # excepted if lineA is already an insert from a
                        # previous diff: in this case, we keep the "old"
                        # version: the new one is the same, but for which we
                        # don't remember who updated it.
                        if (pastAction == 'insert') and (lineA == seqB[j]):
                            res.append( ('equal', seqA[i]) )
                        else:
                            res.append(('replace', (lineA, seqB[j],
                                                    innerDiffs, outerTag)))
                        k = j+1
                        break
                if not similarFound: res.append( ('delete', seqA[i]) )
            i += 1
        # Consider any "unconsumed" line from p_seqB as being inserted.
        if k < len(seqB):
            for line in seqB[k:]: res.append( ('insert', line) )
        return res

    def split(self, s, sep):
        '''Splits string p_s with p_sep. If p_sep is a space, the split can't
           happen for a leading or trailing space, which must be considered as
           being part of the first or last word.'''
        # Manage sep == \n
        if sep == '\n': return s.split(sep)
        leadSpace = s.startswith(sep)
        trailSpace = s.endswith(sep)
        if not leadSpace and not trailSpace: return s.split(sep)
        res = s.strip(sep).split(sep)
        if leadSpace: res[0] = sep + res[0]
        if trailSpace: res[-1] = res[-1] + sep
        return res

    garbage = ('', '\r')
    def removeGarbage(self, l):
        '''Removes from list p_l elements that have no interest, like blank
           strings or considered as is.'''
        i = len(l)-1
        while i >= 0:
            if l[i] in self.garbage: del l[i]
            i -= 1
        return l

    def getHtmlDiff(self, old, new, sep):
        '''Returns the differences between p_old and p_new. Result is a string
           containing the comparison in HTML format. p_sep is used for turning
           p_old and p_new into sequences. If p_sep is a carriage return, this
           method is used for performing a whole diff between 2 strings splitted
           into sequences of lines; if sep is a space, the diff is a
           word-by-word comparison within 2 lines that have been detected as
           similar in a previous call to m_getHtmlDiff with sep=carriage
           return.'''
        res = []
        a = self.split(old, sep)
        b = self.split(new, sep)
        matcher = difflib.SequenceMatcher()
        matcher.set_seqs(a,b)
        for action, i1, i2, j1, j2 in matcher.get_opcodes():
            chunkA = self.removeGarbage(a[i1:i2])
            chunkB = self.removeGarbage(b[j1:j2])
            toAdd = None
            if action == 'equal':
                if chunkA: toAdd = sep.join(chunkA)
            elif action == 'insert':
                if chunkB:
                    toAdd = self.getModifiedChunk(chunkB, action, sep)
            elif action == 'delete':
                if chunkA:
                    toAdd = self.getModifiedChunk(chunkA, action, sep)
            elif action == 'replace':
                if not chunkA and not chunkB:
                    toAdd = ''
                elif not chunkA:
                    # Was an addition, not a replacement
                    toAdd = self.getModifiedChunk(chunkB, 'insert', sep)
                elif not chunkB:
                    # Was a deletion, not a replacement
                    toAdd = self.getModifiedChunk(chunkA, 'delete', sep)
                else: # At least, a true replacement
                    if sep == '\n':
                        # We know that some lines have been replaced from a to
                        # b. By identifying similarities between those lines,
                        # consider some as having been deleted, modified or
                        # inserted.
                        toAdd = ''
                        for sAction, line in self.getSeqDiff(chunkA, chunkB):
                            if sAction in ('insert', 'delete'):
                                toAdd += self.getModifiedChunk(line,sAction,sep)
                            elif sAction == 'equal':
                                toAdd += line
                            elif sAction == 'replace':
                                lineA, lineB, previousDiffsA, outerTag = line
                                # Investigate further here and explore
                                # differences at the *word* level between lineA
                                # and lineB. As a preamble, and in order to
                                # restrict annoyances due to the presence of
                                # XHTML tags, we will compute start and end
                                # parts wich are similar between lineA and
                                # lineB: they may correspond to opening and
                                # closing XHTML tags.
                                i, ja, jb = self.getStringDiff(lineA, lineB)
                                diff = self.getHtmlDiff(lineA[i:ja],
                                                        lineB[i:jb], ' ')
                                toAdd += lineB[:i] + diff + lineB[jb:]
                                # Merge potential previous inner diff tags that
                                # were found (but extracted from) lineA.
                                if previousDiffsA:
                                    merger = Merger(lineA, toAdd,
                                                    previousDiffsA, self)
                                    toAdd = merger.merge()
                                # Rewrap line into outerTag if lineA was a line
                                # tagged as previously inserted.
                                if outerTag:
                                    toAdd = outerTag + toAdd + '</div>'
                    else:
                        toAdd = self.getModifiedChunk(chunkA, 'delete', sep)
                        toAdd += self.getModifiedChunk(chunkB, 'insert', sep)
            if toAdd: res.append(toAdd)
        return sep.join(res)

    def get(self):
        '''Produces the result.'''
        return self.getHtmlDiff(self.old, self.new, '\n')
# ------------------------------------------------------------------------------
