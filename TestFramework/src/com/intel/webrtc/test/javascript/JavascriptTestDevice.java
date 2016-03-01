package com.intel.webrtc.test.javascript;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashSet;
import java.util.Hashtable;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.intel.webrtc.test.ClientTestController;
import com.intel.webrtc.test.Logger;
import com.intel.webrtc.test.TestCase;
import com.intel.webrtc.test.TestDevice;
import com.intel.webrtc.test.TestSuite;

import junit.framework.Assert;
/**
 * Logic device of javascript
 * @author bean
 *
 */
public class JavascriptTestDevice extends Assert implements TestDevice {
    // the prefix of test file, in order to figure the test case file from
    // config file of karma
    public static String TAG = "JavascriptTestDevice";
    // TODO: needed?
    private String jsTestSourcePrefix = "test-peerwn";
    private String deviceName = "";
    private ClientTestController controller;
    private HashSet<String> testMethods;
    public String jsConfFile;
    public JavascriptDeviceInfo deviceInfo;
    public Process karmaStartProcess=null;

    public JavascriptTestDevice(String jsTestFile, String jsConfFile) throws IOException {
        this.jsConfFile=jsConfFile;
        this.deviceInfo=new JavascriptDeviceInfo(jsConfFile);
        testMethods = new HashSet<String>();
        String deviceName;
        try {
            deviceName = scanJsTestCaseFile(jsTestFile);
            setName(deviceName);
        } catch (IOException e) {
            Logger.e(TAG, "Error when init JavascritpTestDevice from the source file.");
            e.printStackTrace();
        }
    }

    /**
     * Scan the test file, get the following infos:
     * 1. DeviceName, and call setName();
     * 2. Methods, add into testMethods.
     * there should be only one TestCase and several TestMethods.
     * @param jsfile the javascript test case source file
     * @return
     * @throws IOException
     */
    private String scanJsTestCaseFile(String jsfile) throws IOException {
        String deviceName = null;
        String suitePatStr = "\\s*describe\\(\\s*['\"]([^'\"]+)['\"]\\s*,\\s*function\\(.*";
        Pattern suitePat = Pattern.compile(suitePatStr);
        String casePatStr = "\\s*it\\(\\s*['\"]([^'\"]+)['\"]\\s*,\\s*function\\(.*";
        Pattern casePat = Pattern.compile(casePatStr);
        BufferedReader reader = new BufferedReader(new FileReader(jsfile));
        String line;
        Matcher m1, m2;
        while ((line = reader.readLine()) != null) {
            m1 = suitePat.matcher(line);
            if (m1.find()) {
                // this line contains the TestDevice name. 'describe' block.
                if (deviceName == null) {
                    // not assigned yet
                    deviceName = m1.group(1);
                } else {
                    // error, multiple 'describe' block in one test file.
                    Logger.e(TAG, "multiple 'describe' block in test file:" + jsfile);
                }
            }
            m2 = casePat.matcher(line);
            if (m2.find()) {
                // this line contains the testMethod
                testMethods.add(m2.group(1));
            }
        }
        reader.close();
        return deviceName;
    }

    @Override
    public String getName() {
        return deviceName;
    }

    @Override
    public void setName(String name) {
        this.deviceName = name;
    }

    /**
     * Scan the javascript test file, and add test case into testSuite.
     * @param TestSuite the test suite.
     */
    @Override
    public void addDeviceToSuite(TestSuite testSuite) {
        Hashtable<String, TestCase> testCases = testSuite.getTestCases();
        for (String method : testMethods) {
            if (testCases.containsKey(method)) {
                // the method have already been added
                testCases.get(method).addDevice(this);
            } else {
                TestCase newTestCase = new TestCase(method);
                newTestCase.addDevice(this);
                testCases.put(method, newTestCase);
            }
        }
    }

    @Override
    public String toString() {
        String ret = "JSDevice:" + deviceName + "\nTest Methods:";
        for (String method : testMethods) {
            ret += method + "\t";
        }
        ret += "\n";
        return ret;
    }
}