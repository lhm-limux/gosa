#-*- coding: utf-8 -*-
import sys
import test_NoseXUnit

import nosexunit.core as ncore

class TestStdRecorder(test_NoseXUnit.TestCase):
    
    def test_std_out_record_on(self):
        recorder = ncore.StdOutRecoder()
        recorder.start()
        sys.stdout.write('hello')
        recorder.stop()
        recorder.end()
        self.assertEquals("hello", recorder.content())
        
    def test_std_out_record_off(self):
        recorder = ncore.StdOutRecoder()
        sys.stdout.write('hello1')
        recorder.start()
        sys.stdout.write('hello2')
        recorder.stop()
        sys.stdout.write('hello3')
        recorder.end()
        self.assertEquals("hello2", recorder.content())    

    def test_std_out_record_reset(self):
        recorder = ncore.StdOutRecoder()
        recorder.start()
        sys.stdout.write('hello')
        recorder.reset()
        sys.stdout.write('hello3')
        recorder.end()
        self.assertEquals("hello3", recorder.content())   

    def test_std_err_record_on(self):
        recorder = ncore.StdErrRecorder()
        recorder.start()
        sys.stderr.write('hello')
        recorder.stop()
        recorder.end()
        self.assertEquals("hello", recorder.content())
        
    def test_std_err_record_off(self):
        recorder = ncore.StdErrRecorder()
        sys.stderr.write('hello1')
        recorder.start()
        sys.stderr.write('hello2')
        recorder.stop()
        sys.stderr.write('hello3')
        recorder.end()
        self.assertEquals("hello2", recorder.content())    

    def test_std_err_record_reset(self):
        recorder = ncore.StdErrRecorder()
        recorder.start()
        sys.stderr.write('hello')
        recorder.reset()
        sys.stderr.write('hello3')
        recorder.end()
        self.assertEquals("hello3", recorder.content())   

        
if __name__=="__main__":
    test_NoseXUnit.main()
