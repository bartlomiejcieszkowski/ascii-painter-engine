class StringHelper:
    @staticmethod
    def multisplit(text: str, separators: str):
        result = []
        start_idx = 0
        idx = 0
        end = len(text)
        while idx < end:
            if text[idx] in separators:
                # '  a, b'
                # idx = 0, last_idx = 0
                if start_idx != idx:
                    # don't create empty zero len words
                    result.append(text[start_idx:idx])
                start_idx = idx + 1
            idx += 1
        if start_idx != idx:
            # last word
            result.append(text[start_idx:idx])
        return result

    @staticmethod
    def split_trim(text: str, separator):
        result = []
        for token in text.split(separator):
            token = token.strip()
            if token:
                result.append(token)
        return result
