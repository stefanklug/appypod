# ------------------------------------------------------------------------------
import re, difflib

# ------------------------------------------------------------------------------
innerDiff = re.compile('<span name="(insert|delete)".*? title="(.*?)">' \
                       '(.*?)</span>')
htmlTag = re.compile('<(?P<tag>\w+)( .*?)?>(.*)</(?P=tag)>')

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

    def manageOverlap(self, oldDiff):
        '''p_oldDiff is a previously inserted text from self.lineA. This text
           is not found anymore at the start of self.lineB[self.i:]: it means
           that an overlapping diff exists among new diffs. We will manage this
           by identifying several, cutted, "insert" and/or "edit" zones.'''
        # The idea here is to "consume" the old inserted text until we have
        # found, within the new diff, all updates that have been performed on
        # this old text. Then, we will have found the complete "zone" that was
        # impacted by both old and new diffs.
        oldText = oldDiff.group(3)
        res = ''
        while oldText:
            # Get the overlapping (new) diff.
            newDiff, newDiffStart, isPrevious = self.getNextDiff()
            if not newDiff:
                # No more new diff. So normally, we should find what remains in
                # oldText at self.lineB[self.i:]
                if not self.lineB[self.i:].startswith(oldText):
                    # Anormal additional char. Probably a space? Indeed,
                    # word-level comparisons imply split(' ') which can be
                    # error-prone.
                    res += self.lineB[self.i]
                    self.i += 1
                    if not self.lineB[self.i:].startswith(oldText):
                        raise 'Error!!!!'
                res += self.differ.getModifiedChunk(oldText, 'insert', '',
                                                    msg=oldDiff.group(2))
                self.i += len(oldText)
                oldText = ''
                break
            # Dump the part of the old text that has been untouched by the new
            # diff.
            if self.i < newDiffStart:
                untouched = self.lineB[self.i:newDiffStart]
                res += self.differ.getModifiedChunk(untouched, 'insert', '',
                                                    msg=oldDiff.group(2))
                self.i = newDiffStart
                oldText = oldText[len(untouched):]
            # Manage the new diff
            res += newDiff.group(0)
            self.i += len(newDiff.group(0))
            self.deltaPrevious += len(newDiff.group(0))
            if newDiff.group(1) == 'delete':
                # Consume oldText, that was deleted, at least partly, by
                # this diff.
                if len(newDiff.group(3)) >= len(oldText):
                    # We have consumed oldText in its entirety
                    oldText = ''
                else:
                    oldText = oldText[len(newDiff.group(3)):]
                self.deltaPrevious -= len(newDiff.group(3))
        return res

    def merge(self):
        '''Merges self.previousDiffs into self.lineB.'''
        res = ''
        print 'MERGE'
        print 'Line A', self.lineA
        print 'Line B', self.lineB
        diff, diffStart, isPrevious = self.getNextDiff()
        while diff:
            # Dump the part of lineB between self.i and diffStart
            res += self.lineB[self.i:diffStart]
            self.i = diffStart
            if isPrevious:
                if diff.group(1) == 'insert':
                    # Check if the inserted text is still present in lineB
                    if self.lineB[self.i:].startswith(diff.group(3)):
                        # Yes. Dump the diff and go ahead within lineB
                        res += diff.group(0)
                        self.i += len(diff.group(3))
                    else:
                        # The inserted text can't be found as is in lineB.
                        # Must have been (partly) re-edited or removed.
                        
                        overlap = self.manageOverlap(diff)
                        res += overlap
                elif diff.group(1) == 'delete':
                    res += diff.group(0)
            else:
                # Dump the diff and update self.i
                res += diff.group(0)
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

    def __init__(self, old, new,
                 insertMsg='Inserted text', deleteMsg='Deleted text',
                 insertCss=None, deleteCss=None, insertName='insert',
                 deleteName='delete', diffRatio=0.7):
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
        # This tag will get a "name" attribute whose content will be
        # p_insertName or p_deleteName
        self.insertName = insertName
        self.deleteName = deleteName
        # The diff algorithm of this class will need to identify similarities
        # between strings. Similarity ratios will be computed by using method
        # difflib.SequenceMatcher.ratio (see m_isSimilar below). Strings whose
        # comparison will produce a ratio above p_diffRatio will be considered
        # as similar.
        self.diffRatio = diffRatio
        # Some computed values
        for tag in ('div', 'span'):
            for type in ('insert', 'delete'):
                setattr(self, '%s%sPrefix' % (tag, type.capitalize()),
                        '<%s name="%s"' % (tag, getattr(self, '%sName' % type)))

    def getModifiedChunk(self, seq, type, sep, msg=None):
        '''p_sep.join(p_seq) (if p_seq is a list) or p_seq (if p_seq is a
           string) is a chunk that was either inserted (p_type='insert') or
           deleted (p_type='delete'). This method will surround this part with
           a div or span tag that will get some CSS class allowing to highlight
           the update. If p_msg is given, it will be used instead of the default
           p_type-related message stored on p_self.'''
        # Will the surrouding tag be a div or a span?
        if sep == '\n': tag = 'div'
        else: tag = 'span'
        # What message will it show in its 'title' attribute?
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
        # by a tag. This way, we know that a surrounding tag can't span several
        # lines, which is a prerequisite for managing cumulative diffs.
        if sep == ' ':
            if not isinstance(seq, basestring):
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
        '''p_diff is a regex containing an insert or delete that was found
           within line. This function applies the diff, removing or inserting
           the diff into p_line.'''
        # Keep content only for "insert" tags.
        content = ''
        if diff.group(1) == 'insert':
            content = diff.group(3)
        return line[:diff.start()] + content + line[diff.end():]

    def isSimilar(self, s1, s2):
        '''Returns True if strings p_s1 and p_s2 can be considered as
           similar.'''
        ratio = difflib.SequenceMatcher(a=s1.lower(), b=s2.lower()).ratio()
        return ratio > self.diffRatio

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
             removed and placed into "outerTag" (a re.MatchObject from regex
             innerHtml, see above);
           * if inner diff tags (insert or delete) are found. In that case,
             - if inner "insert" tags are found, they are removed but their
               content is kept;
             - if inner "delete" tags are found, they are removed, content
               included;
             - "innerDiffs" holds the list of re.MatchObject instances
               representing the found inner tags.
        '''
        if line.startswith(self.divDeletePrefix):
            return ('delete', line, None, None)
        if line.startswith(self.divInsertPrefix):
            # Return the line without the surrounding tag.
            action = 'insert'
            outerTag = htmlTag.match(line)
            line = outerTag.group(3)
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

    def computeTag(self, regexTag, content):
        '''p_regexTag is a re.MatchObject from regex htmlTag. p_content is a
           new content to put within this tag. This method produces the new
           string tag filled with p_content.'''
        # Recompute start tag from p_regexTag
        startTag = '<%s' % regexTag.group(1)
        # Add tag attributes if found
        if regexTag.group(2):
            startTag += regexTag.group(2)
        startTag += '>'
        # Recompute end tag
        endTag = '</%s>' % regexTag.group(1)
        # Wrap content info reified tag
        return startTag + content + endTag

    def getSeqDiff(self, seqA, seqB, sep):
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
        # Merge similar diffs, excepted if separator is a carriage return
        if sep == '\n': return res
        newRes = []
        lastType = None
        for type, data in res:
            if lastType and (type != 'replace') and (lastType == type):
                newRes[-1] = (type, newRes[-1][1] + sep + data)
            else:
                newRes.append( (type, data) )
            lastType = type
        return newRes

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

    nextSeps = {'\n': ' ', ' ': ''}
    def getReplacement(self, sep, lineA, lineB, previousDiffsA, outerTagA):
        '''p_lineA has been replaced with p_lineB. Here, we will investigate
           further here and explore differences at the *word* level between
           p_lineA and p_lineB.

           p_previousDiffsA may contain a series of updates (inserts, deletions)
           that have already been performed on p_lineA.

           If p_lineA was a previously inserted line, p_lineA comes without his
           outer tag, that lies in p_outerTagA (as a re.MatchObject instance
           computed from regex htmlTag). In that case, we will wrap the result
           with that tag.'''
        # As a preamble, and in order to restrict annoyances due to the presence
        # of XHTML tags, we will remove start and end tags from p_lineA and
        # p_lineB if present.
        matchA = htmlTag.match(lineA)
        contentA = matchA and matchA.group(3) or lineA
        matchB = htmlTag.match(lineB)
        contentB = matchB and matchB.group(3) or lineB
        # Perform the diff at the level of words
        diff = self.getHtmlDiff(contentA, contentB, self.nextSeps[sep])
        if matchB:
            res = self.computeTag(matchB, diff)
        else:
            res = diff
        # Merge potential previous inner diff tags that
        # were found (but extracted from) lineA.
        if previousDiffsA:
            merger = Merger(lineA, res, previousDiffsA, self)
            res = merger.merge()
        # Rewrap line into outerTagA if lineA was a line tagged as previously
        # inserted.
        if outerTagA:
            res = self.computeTag(outerTagA, res)
        return res

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
        if sep:
            a = self.split(old, sep)
            b = self.split(new, sep)
        else:
            a = old
            b = new
        matcher = difflib.SequenceMatcher()
        matcher.set_seqs(a, b)
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
                    toAdd = []
                    # We know that some lines/words have been replaced from a to
                    # b. By identifying similarities between those lines/words,
                    # consider some as having been deleted, modified or
                    # inserted.
                    for sAction, line in self.getSeqDiff(chunkA, chunkB, sep):
                        if sAction in ('insert', 'delete'):
                            mChunk = self.getModifiedChunk(line, sAction, sep)
                            toAdd.append(mChunk)
                        elif sAction == 'equal':
                            toAdd.append(line)
                        elif sAction == 'replace':
                            toAdd.append(self.getReplacement(sep, *line))
                    # The following line, when sep is the space (=when workin
                    # on diffs at the word level), leads to additional spaces
                    # being dumped into the result (ie, a space between a delete
                    # and an insert, which was not in the initial text). We
                    # could not find a way to avoid inserting those spaces. So
                    # when merging diffs (see Merger.merge), we know that a
                    # 'space' error can occur and we take it into account then.
                    toAdd = sep.join(toAdd)
            if toAdd: res.append(toAdd)
        return sep.join(res)

    def get(self):
        '''Produces the result.'''
        return self.getHtmlDiff(self.old, self.new, '\n')
# ------------------------------------------------------------------------------
