import React, { useState } from "react";
import axios from "axios";
import ReactLoading from "react-loading";
import ComparisonModal from "./ComparisonModal";
import { FaTimesCircle } from "react-icons/fa";
import { ArrowLeft, CheckCircle } from "lucide-react";
import ModalLoadingScreen from "../../LoadingScreen/ModalLoadingScreen";
import AlertMessage from "../../Alert/Alert";
import { QA_URL } from "../../util/config";

const CompareAnswerModel = ({ onBack }) => {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [answerType, setAnswerType] = useState("structured");
  const [feedback, setFeedback] = useState(null);
  const [modelAnswer, setModelAnswer] = useState("");
  const [relatedWebsites, setRelatedWebsites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [alert, setAlert] = useState({message:"", type:""});
  const [studentId,setStudentId] = useState("")

  const handleCompareAnswer = async () => {
    if (!question) {
      setAlert({ message: "Please enter a question!", type: "warning" });
      return;
    }
    
    if (!answer) {
      setAlert({ message: "Please enter a answer!", type: "warning" });
      return;
    }
    
    if (!answerType) {
      setAlert({ message: "Please select an answer type!", type: "warning" });
      return;
    }

    let storedStudentId = localStorage.getItem("user");
    if (storedStudentId) {
      storedStudentId = JSON.parse(storedStudentId).email;
      setStudentId(storedStudentId);
    }
    

    setLoading(true);
    setFeedback(null);
    setModelAnswer("");
    setRelatedWebsites([]);

    try {
      const response = await axios.post(`${QA_URL}/evaluate-answer`, {
        student_id: storedStudentId,
        question,
        user_answer: answer,
        question_type: answerType,
      });

      setFeedback(response.data.evaluation_result);
      setModelAnswer(response.data.model_answer);
      setRelatedWebsites(response.data.related_websites || []);

      setShowModal(true);
    } catch (error) {
      console.error("Error comparing answer:", error.response.data.detail);
      //alert("Failed to compare answer. Please try again.");
      setAlert({message:"Failed to compare answer: " + error.response.data.detail, type:"error"});
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
          {alert.message && <AlertMessage message={alert.message} type={alert.type} onClose={() => setAlert({ message: "", type: "" })} />}

      <div className="bg-gray-100 p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Compare Answer</h3>

        <div className="mb-4">
          <label className="block text-gray-700 font-medium mb-2">Question</label>
          <input
            type="text"
            placeholder="Enter your question..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            className="w-full border border-gray-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
          />
        </div>

        <div className="mb-4">
          <label className="block text-gray-700 font-medium mb-2">Answer Type</label>
          <select
            value={answerType}
            onChange={(e) => setAnswerType(e.target.value)}
            disabled={loading}
            className="w-full border border-gray-300 p-3 rounded-lg bg-white focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
          >
            <option value="structured">Structured</option>
            <option value="essay">Essay</option>
          </select>
        </div>

        <div className="mb-4">
          <label className="block text-gray-700 font-medium mb-2">Your Answer</label>
          <textarea
            placeholder="Enter your answer..."
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={loading}
            className="w-full border border-gray-300 p-3 rounded-lg h-24 resize-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
          ></textarea>
        </div>

        {loading && (
          <ModalLoadingScreen />
        )}

<div className="flex flex-wrap justify-between gap-4 mt-4 w-full">
  <button
    className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-6 py-3 border-2 border-[#140342] text-white bg-[#140342] font-semibold rounded-lg 
      transition-transform duration-300 hover:scale-105 hover:bg-[#32265a]"
    onClick={onBack}
    disabled={loading}
  >
    <ArrowLeft size={20} /> Back
  </button>

  <button
    onClick={handleCompareAnswer}
    disabled={loading}
    className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-6 py-3 border-2 border-[#00FF84] text-[#140342] bg-[#00FF84] font-semibold rounded-lg 
      transition-transform duration-300 hover:scale-105 hover:bg-[#00cc70]"
  >
    <CheckCircle size={20} /> Compare Answer
  </button>
</div>

      </div>

      <ComparisonModal
        showModal={showModal}
        loading={loading}
        feedback={feedback}
        modelAnswer={modelAnswer}
        answer={answer}
        relatedWebsites={relatedWebsites}
        onClose={() => setShowModal(false)}
      />
    </div>
  );
};

export default CompareAnswerModel;